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
	"context"
	"database/sql"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

// LogicalDumperMysqldump logical dumper using mysqldump tool
type LogicalDumperMysqldump struct {
	cnf          *config.BackupConfig
	dbbackupHome string
	backupInfo   dbareport.IndexContent // for mysqldump backup
	dbConn       *sql.DB
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

	if len(l.cnf.LogicalBackup.Databases) > 0 && len(dbList) >= 2 {
		if len(l.cnf.LogicalBackup.Tables) == 0 { // 仅有 databases
			args = append(args, "--databases")
			args = append(args, dbList...)
		} else {
			return nil, errors.Errorf("mysqldump --tables cannot be used with multi databases")
		}
	} else if len(l.cnf.LogicalBackup.Databases) > 0 && len(dbList) == 1 { // 只有一个 db，可以指定 table
		args = append(args, l.cnf.LogicalBackup.Databases)
		args = append(args, tbList...)
	} else if len(l.cnf.LogicalBackup.ExcludeDatabases) > 0 {
		if len(l.cnf.LogicalBackup.ExcludeTables) == 0 {
			logger.Log.Info("get database list from db to exclude:")
			l.dbConn, err = mysqlconn.InitConn(&l.cnf.Public)
			if err != nil {
				return nil, err
			}
			defer func() {
				_ = l.dbConn.Close()
			}()
			if allDatabases, err := mysqlconn.GetDatabases("", l.dbConn); err != nil {
				return nil, err
			} else {
				dbListExclude = append(dbListExclude, "information_schema", "performance_schema")
				for _, d := range dbListExclude {
					allDatabases = cmutil.StringsRemove(allDatabases, d)
				}
				args = append(args, "--databases", strings.Join(allDatabases, " "))
			}
		} else {
			return nil, errors.Errorf("mysqldump exclude is not allowed, exclude-databases=%s, exclude-tables=%s",
				dbListExclude, tbListExclude)
		}
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

// Execute excute dumping backup with logical backup tool[mysqldump]
func (l *LogicalDumperMysqldump) Execute(enableTimeOut bool) (err error) {
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
		"--single-transaction", "--master-data=2",
		"--max-allowed-packet=1G", "--no-autocommit",
		"--set-gtid-purged=off",
		//"--default-character-set  //
	}
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
	if filterType == config.FilterTypeForm {
		if filterArgs, err := l.buildArgsTableFilter(); err != nil {
			return err
		} else {
			args = append(args, filterArgs...)
		}
	} else if filterType == config.FilterTypeEmpty {
		return errors.New("please give --databases / --exclude-databases to dump")
	}
	args = append(args, "-r",
		filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName(), l.cnf.Public.TargetName()+".sql"))

	var cmd *exec.Cmd
	if enableTimeOut {
		timeDiffUnix, err := GetMaxRunningTime(l.cnf.Public.BackupTimeOut)
		if err != nil {
			return err
		}
		ctx, cancel := context.WithTimeout(context.Background(), (time.Duration(timeDiffUnix))*time.Second)
		defer cancel()

		cmd = exec.CommandContext(ctx,
			"sh", "-c",
			fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " ")))
	} else {
		cmd = exec.Command("sh", "-c",
			fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " ")))
	}

	logger.Log.Info("logical dump command with mysqldump: ", cmd.String())

	outFile, err := os.Create(
		filepath.Join(
			l.dbbackupHome,
			"logs",
			fmt.Sprintf("mysqldump_%d.log", int(time.Now().Weekday()))))
	if err != nil {
		logger.Log.Error("create log file failed: ", err)
		return err
	}
	defer func() {
		_ = outFile.Close()
	}()
	cmd.Stdout = outFile
	cmd.Stderr = outFile

	mysqldumpBeginTime := time.Now().Format("2006-01-02 15:04:05")
	l.backupInfo.BackupBeginTime, err = time.ParseInLocation(cst.MydumperTimeLayout, mysqldumpBeginTime, time.Local)
	if err != nil {
		return errors.Wrapf(err, "parse BackupBeginTime(mysqldump) %s", mysqldumpBeginTime)
	}
	err = cmd.Run()
	if err != nil {
		logger.Log.Error("run logical backup(with mysqldump) failed: ", err)
		return err
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
	metadata, err := parseMysqldumpMetadata(metaFileName)
	if err != nil {
		return nil, errors.WithMessage(err, "parse mysqldump metadata")
	}
	metaInfo.BackupBeginTime = l.backupInfo.BackupBeginTime
	metaInfo.BackupEndTime = l.backupInfo.BackupEndTime
	metaInfo.BackupConsistentTime = metaInfo.BackupBeginTime
	metaInfo.BinlogInfo.ShowMasterStatus = &dbareport.StatusInfo{
		BinlogFile: metadata.MasterStatus["File"],
		BinlogPos:  metadata.MasterStatus["Position"],
		MasterHost: cnf.Public.MysqlHost, // use backup_host as local binlog file_pos host
		MasterPort: cast.ToInt(cnf.Public.MysqlPort),
	}
	if strings.ToLower(cnf.Public.MysqlRole) == cst.RoleSlave {
		metaInfo.BinlogInfo.ShowSlaveStatus = &dbareport.StatusInfo{
			BinlogFile: metadata.SlaveStatus["File"],
			BinlogPos:  metadata.SlaveStatus["Position"],
			//Gtid:       metadata.SlaveStatus["Executed_Gtid_Set"],
			//MasterHost: metadata.SlaveStatus["Master_Host"],
			//MasterPort: cast.ToInt(metadata.SlaveStatus["Master_Port"]),
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
