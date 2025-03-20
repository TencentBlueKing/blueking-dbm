/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package backupexe

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"time"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

// LogicalDumperMysqldump logical dumper using mysqldump tool
type LogicalDumperMysqldump struct {
	cnf          *config.BackupConfig
	backupInfo   dbareport.IndexContent // for mysqldump backup
	dbConn       *sqlx.Conn
	dbbackupHome string

	masterStatus *dbareport.StatusInfo
	slaveStatus  *dbareport.StatusInfo
}

// initConfig initializes the configuration for the logical dumper[mysqldump]
func (l *LogicalDumperMysqldump) initConfig(mysqlVerStr string) error {
	if l.cnf == nil {
		return errors.New("logical dumper[mysqldump] params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		l.dbbackupHome = filepath.Dir(cmdPath)
	}
	BackupTool = cst.ToolMysqldump
	return nil
}

func (l *LogicalDumperMysqldump) buildArgsTableFilter() (args []string, err error) {
	dbList := strings.Split(l.cnf.LogicalBackup.Databases, ",")
	tbList := strings.Split(l.cnf.LogicalBackup.Tables, ",")
	dbListExclude := strings.Split(l.cnf.LogicalBackup.ExcludeDatabases, ",")
	tbListExclude := strings.Split(l.cnf.LogicalBackup.ExcludeTables, ",")
	// 把默认排除的系统库补充进去
	var dbListExcludeNew []string
	for _, db := range cst.SysDbsExcludeForFull {
		if !slices.Contains(dbListExclude, db) {
			dbListExcludeNew = append(dbListExcludeNew, db)
		}
	}
	dbListExcludeNew = append(dbListExcludeNew, dbListExclude...)
	dbListExclude = dbListExcludeNew
	var dbListFiltered []string
	if filter, err := db_table_filter.NewFilter(dbList, tbList, dbListExclude, tbListExclude); err != nil {
		return nil, err
	} else {
		l.dbConn, err = mysqlconn.InitConnx(&l.cnf.Public, context.Background())
		if err != nil {
			return nil, err
		}
		defer func() {
			_ = l.dbConn.Close()
		}()
		dbListFiltered, err = filter.GetDbsByConn(l.dbConn)
		if err != nil {
			return nil, errors.WithMessage(err, "get database from instance")
		}
	}
	logger.Log.Infof("database filtered:%v, tables:%v, excludeTables:%v", dbListFiltered, tbList, tbListExclude)

	// mysqldump 条件：
	// databases, exclude-databases 允许模糊匹配
	// tables 不允许模糊匹配
	// exclude-tables 只能为空
	// 简单说 mysqldump 支持 --database db1 db2 db3, 或者 db1 table1 table2
	if l.cnf.LogicalBackup.Tables == "*" && l.cnf.LogicalBackup.ExcludeTables == "" {
		args = append(args, "--databases")
		args = append(args, dbListFiltered...)
	} else if len(dbListFiltered) == 1 && l.cnf.LogicalBackup.ExcludeTables == "" { // 只有一个 db，可以指定 table
		args = append(args, dbListFiltered...)
		args = append(args, tbList...)
	} else if strings.Contains(l.cnf.LogicalBackup.Tables, "%") {
		return nil, errors.Errorf("mysqldump does not support table like %s", l.cnf.LogicalBackup.Tables)
	} else if l.cnf.LogicalBackup.ExcludeTables != "" {
		return nil, errors.Errorf("mysqldump does not support table exclude %s", l.cnf.LogicalBackup.ExcludeTables)
	} else if len(dbListFiltered) >= 2 && len(tbList) > 0 {
		return nil, errors.Errorf("mysqldump --tables cannot be used with multi databases %v", dbListFiltered)
	} else {
		return nil, errors.Errorf("mysqldump exclude not not support, exclude-databases=%s, exclude-tables=%s",
			dbListExclude, tbListExclude)
	}
	return args, nil
}

func (l *LogicalDumperMysqldump) buildArgsObjectFilter() (args []string) {
	if l.cnf.Public.DataSchemaGrant == "" {
		if l.cnf.LogicalBackup.NoData {
			args = append(args, "--no-data")
		}
		if l.cnf.LogicalBackup.NoSchemas {
			args = append(args, "--no-create-info --no-create-db") // -t -n
		}
		if l.cnf.LogicalBackup.Events {
			args = append(args, "-E") // --events
		}
		if l.cnf.LogicalBackup.Routines {
			args = append(args, "-R") // --routines
		}
		if l.cnf.LogicalBackup.Triggers {
			args = append(args, "--triggers")
		} else {
			args = append(args, "--skip-triggers")
		}
		if l.cnf.LogicalBackup.InsertMode == "replace" {
			args = append(args, "--replace")
		} else if l.cnf.LogicalBackup.InsertMode == "insert_ignore" {
			args = append(args, "--insert-ignore")
		}
	} else {
		if l.cnf.Public.IfBackupSchema() && !l.cnf.Public.IfBackupData() {
			args = append(args, []string{
				"--no-data", "--events", "--routines", "--triggers",
			}...)
		} else if !l.cnf.Public.IfBackupSchema() && l.cnf.Public.IfBackupData() {
			args = append(args, []string{
				"--no-create-info", "--no-create-db",
			}...)
		} else if l.cnf.Public.IfBackupSchema() && l.cnf.Public.IfBackupData() {
			args = append(args, []string{
				"--events", "--routines", "--triggers",
			}...)
		}
	}
	return args
}

// MysqldumpHasOption check mysqldump has --xxx or not
func MysqldumpHasOption(bin string, option string) (bool, error) {
	// 注意 --help 要在后面
	_, cmdStderr, err := cmutil.ExecCommand(false, "", bin, option, "--help")
	if err == nil {
		return true, nil
	}
	if strings.Contains(cmdStderr, "unknown option") {
		return false, nil
	} else {
		return false, err
	}
}

// Execute execute dumping backup with logical backup tool[mysqldump]
func (l *LogicalDumperMysqldump) Execute(ctx context.Context) (err error) {
	var binPath string
	if l.cnf.LogicalBackupMysqldump.BinPath != "" {
		binPath = l.cnf.LogicalBackupMysqldump.BinPath
	} else {
		binPath = filepath.Join(l.dbbackupHome, "/bin/mysqldump")
		if !cmutil.FileExists(binPath) {
			binPath, err = exec.LookPath("mysqldump")
			if err != nil {
				return err
			}
		}
	}
	logger.Log.Info("user mysqldump path:", binPath)

	errCreatDir := os.Mkdir(filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName()), 0755)
	if errCreatDir != nil {
		logger.Log.Error("failed to create mysqldump dir, err:", errCreatDir)
		return errCreatDir
	}

	args := []string{
		"-h", l.cnf.Public.MysqlHost,
		"-P", strconv.Itoa(l.cnf.Public.MysqlPort),
		"-u" + l.cnf.Public.MysqlUser,
		"-p" + l.cnf.Public.MysqlPasswd,
		"--skip-opt", "--create-options", "--extended-insert", "--quick",
		"--master-data=2",
		"--max-allowed-packet=1G", "--no-autocommit",
		"--hex-blob",
	}
	if *l.cnf.LogicalBackup.TrxConsistencyOnly {
		args = append(args, "--single-transaction")
	}
	if ok, _ := MysqldumpHasOption(binPath, "--set-gtid-purged"); ok { // // 5.7 需要off 如果支持
		args = append(args, "--set-gtid-purged=off")
	}
	args = append(args, "--default-character-set", l.cnf.Public.MysqlCharset)
	if l.cnf.Public.MysqlRole == cst.RoleSlave {
		args = append(args, []string{
			"--dump-slave=2", // will stop slave sql_thread
		}...)
		defer StartSlaveSqlThread(l.cnf)
	}

	// use LogicalDump option
	args = append(args, l.buildArgsObjectFilter()...)

	if l.cnf.LogicalBackupMysqldump.ExtraOpt != "" {
		args = append(args, []string{
			fmt.Sprintf(`%s`, l.cnf.LogicalBackupMysqldump.ExtraOpt),
		}...)
	}
	filterType := l.cnf.LogicalBackup.GetFilterType()
	if filterType == config.FilterTypeRegex {
		return errors.New("mysqldump does not support regex filter")
	} else if filterType == config.FilterTypeForm {
		if filterArgs, err := l.buildArgsTableFilter(); err != nil {
			return err
		} else {
			args = append(args, filterArgs...)
		}
	} else if filterType == config.FilterTypeEmpty {
		return errors.New("please give --databases / --exclude-databases for mysqldump")
	}
	outSqlFile := filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName(), l.cnf.Public.TargetName()+".sql")
	if l.cnf.LogicalBackup.DisableCompress {
		args = append(args, "-r", outSqlFile)
	} else {
		// 注意这里用了管道
		// bash -c "aaa | bbb" 只要 bbb 命令没报错，返回值一直是 0，所有不能根据 return code 判断命令成功失败，而要从 stderr 判断
		args = append(args, "|", CmdZstd, "-q", "-f", "-o", outSqlFile+cst.ZstdSuffix)
	}
	var cmd *exec.Cmd
	cmd = exec.CommandContext(ctx, "bash", "-c", fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " ")))
	logger.Log.Info("logical dump command with mysqldump: ", cmd.String())

	mysqldumpLogFile := filepath.Join(logger.GetLogDir(),
		fmt.Sprintf("mysqldump_%d_%d.log", l.cnf.Public.MysqlPort, int(time.Now().Weekday())))
	outFile, err := os.OpenFile(mysqldumpLogFile, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0644)
	if err != nil {
		logger.Log.Error("create log file failed: ", err)
		return err
	}
	defer func() {
		_ = outFile.Close()
	}()
	cmd.Stdout = outFile
	var stderr bytes.Buffer

	errWriter := io.MultiWriter(outFile, &stderr)
	cmd.Stderr = errWriter

	mysqldumpBeginTime := time.Now().Format("2006-01-02 15:04:05")
	l.backupInfo.BackupBeginTime, err = time.ParseInLocation(cst.MydumperTimeLayout, mysqldumpBeginTime, time.Local)
	if err != nil {
		return errors.Wrapf(err, "parse BackupBeginTime(mysqldump) %s", mysqldumpBeginTime)
	}

	db, err := mysqlconn.InitConn(&l.cnf.Public)
	if err != nil {
		logger.Log.Errorf("can not connect to the mysql, host:%s, port:%d, errmsg:%s",
			l.cnf.Public.MysqlHost, l.cnf.Public.MysqlPort, err)
		return err
	}
	defer func() {
		_ = db.Close()
	}()
	// 屏蔽本地 mysql-monitor slave-status 监控
	if showMasterStatus, err := mysqlconn.ShowMysqlMasterStatus(false, db); err != nil {
		return err
	} else {
		l.masterStatus = &dbareport.StatusInfo{
			BinlogFile: showMasterStatus.File,
			BinlogPos:  cast.ToString(showMasterStatus.Position),
			Gtid:       showMasterStatus.ExecutedGtidSet,
			MasterHost: l.cnf.Public.MysqlHost,
			MasterPort: l.cnf.Public.MysqlPort,
		}
	}
	masterHost, masterPort, err := mysqlconn.ShowMysqlSlaveStatus(db)
	if err != nil {
		return err
	}
	l.slaveStatus = &dbareport.StatusInfo{
		MasterHost: masterHost,
		MasterPort: masterPort,
	}

	err = cmd.Run()
	if err != nil || stderr.String() != "" {
		errStrPrefix := fmt.Sprintf("tail 5 error from %s", mysqldumpLogFile)
		errStrDetail, _ := cmutil.NewGrepLines(mysqldumpLogFile, true, false).MatchWords(nil, 5)
		if len(errStrDetail) > 0 {
			logger.Log.Info(errStrPrefix)
			logger.Log.Error(errStrDetail)
		} else {
			logger.Log.Warn("tail can not find more detail error message from ", mysqldumpLogFile)
		}
		logger.Log.Error("run logical(mysqldump) backup failed", err, l.cnf.Public.MysqlPort)
		if err == nil {
			return errors.Errorf("%s\n%s", errStrPrefix, errStrDetail)
		}
		return errors.WithMessagef(err, fmt.Sprintf("%s\n%s", errStrPrefix, errStrDetail))
	}
	mysqldumpEndTime := time.Now().Format("2006-01-02 15:04:05")
	l.backupInfo.BackupEndTime, err = time.ParseInLocation(cst.MydumperTimeLayout, mysqldumpEndTime, time.Local)
	if err != nil {
		return errors.Wrapf(err, "parse BackupEndTime(mysqldump) %s", mysqldumpEndTime)
	}

	return nil
}

// PrepareBackupMetaInfo prepare the backup result of Logical Backup for mysqldump backup
// 备份完成后，解析 metadata 文件
func (l *LogicalDumperMysqldump) PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error) {
	var metaInfo = dbareport.IndexContent{BinlogInfo: dbareport.BinlogStatusInfo{}}
	metaFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), cnf.Public.TargetName()+".sql")
	if !cnf.LogicalBackup.DisableCompress {
		metaFileName += ".zst"
	}
	metadata, err := parseMysqldumpMetadata(metaFileName)
	if err != nil {
		return nil, errors.WithMessage(err, "parse mysqldump metadata")
	}
	metaInfo.BackupBeginTime = l.backupInfo.BackupBeginTime
	metaInfo.BackupEndTime = l.backupInfo.BackupEndTime
	metaInfo.BackupConsistentTime = metaInfo.BackupBeginTime
	if strings.ToLower(l.cnf.Public.MysqlRole) != cst.RoleSlave { // master / repeater
		// 如果是 master, sql里面的 CHANGE MASTER TO 是本机位点
		metaInfo.BinlogInfo.ShowMasterStatus = &dbareport.StatusInfo{
			BinlogFile: metadata.MasterStatus["File"],
			BinlogPos:  metadata.MasterStatus["Position"],
			MasterHost: l.masterStatus.MasterHost,
			MasterPort: l.masterStatus.MasterPort,
		}
	} else { // slave
		// show_master_status
		metaInfo.BinlogInfo.ShowMasterStatus = l.masterStatus
		// show slave status
		// 如果是 slave, sql里的 CHANGE MASTER TO 是 远端 master的位点。属于 slave status 信息
		metaInfo.BinlogInfo.ShowSlaveStatus = &dbareport.StatusInfo{
			BinlogFile: metadata.MasterStatus["File"],
			BinlogPos:  metadata.MasterStatus["Position"],
			MasterHost: l.slaveStatus.MasterHost,
			MasterPort: l.slaveStatus.MasterPort,
		}
	}
	metaInfo.JudgeIsFullBackup(&cnf.Public)
	return &metaInfo, nil
}

func StartSlaveSqlThread(cnf *config.BackupConfig) error {
	db, err := mysqlconn.InitConn(&cnf.Public)
	if err != nil {
		return err
	}
	defer func() {
		_ = db.Close()
	}()
	logger.Log.Infof("start slave sql_thread for %d", cnf.Public.MysqlPort)
	return mysqlconn.StartSlaveThreads(false, true, db)
}
