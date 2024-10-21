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

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

// LogicalLoaderMysqldump this logical loader is used to load logical backup with mysql(client)
type LogicalLoaderMysqldump struct {
	cnf          *config.BackupConfig
	dbbackupHome string
	dbConn       *sql.DB
	// initConnect load 之前会保留 init_connect 参数，load完成后会恢复
	initConnect string
	// metaInfo 获取备份里面字符集信息
	metaInfo *dbareport.IndexContent
}

// initConfig initializes the configuration for the logical loader[mysql]
func (l *LogicalLoaderMysqldump) initConfig(metaInfo *dbareport.IndexContent) error {
	if l.cnf == nil {
		return errors.New("logical loader params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		l.dbbackupHome = filepath.Dir(cmdPath)
	}
	if l.cnf.LogicalLoad.GetFilterType() != config.FilterTypeEmpty {
		return errors.New("data sql1 files dumped by mysqldump cannot be filter databases or tables")
	}
	if (l.cnf.LogicalLoad.Databases != "" || l.cnf.LogicalLoad.Tables != "" ||
		l.cnf.LogicalLoad.ExcludeDatabases != "" || l.cnf.LogicalLoad.ExcludeTables != "") ||
		l.cnf.LogicalLoad.Regex != "" ||
		l.cnf.LogicalLoad.TablesList != "" {
		return errors.New("data sql2 files dumped by mysqldump cannot be filter databases or tables")
	}
	l.metaInfo = metaInfo
	if l.cnf.LogicalLoad.MysqlCharset == "" {
		l.cnf.LogicalLoad.MysqlCharset = metaInfo.BackupCharset
	}
	return nil
}

// preExecute preprocess before loading data
func (l *LogicalLoaderMysqldump) preExecute() error {
	// 临时清理 init_connect
	dbListDrop := l.cnf.LogicalLoad.DBListDropIfExists
	var initConnect string
	if err := l.dbConn.QueryRow("select @@init_connect").Scan(&initConnect); err != nil {
		return err
	}
	l.initConnect = initConnect
	if l.initConnect != "" && strings.TrimSpace(dbListDrop) != "" {
		logger.Log.Info("set global init_connect='' for safe")
		if _, err := l.dbConn.Exec("set global init_connect=''"); err != nil {
			return err
		}
	}

	// handle DBListDropIfExists
	// 如果有设置这个选项，会在运行前执行 drop database if exists 命令，来清理脏库
	if strings.TrimSpace(dbListDrop) != "" {
		logger.Log.Info("load logical DBListDropIfExists:", dbListDrop)
		if strings.Contains(dbListDrop, "`") {
			return errors.Errorf("DBListDropIfExists has invalid character %s", dbListDrop)
		}
		SysDBs := []string{"mysql", "sys", "information_schema", "performance_schema", "test"}
		dblist := strings.Split(dbListDrop, ",")
		dblistNew := []string{}
		for _, dbName := range dblist {
			dbName = strings.TrimSpace(dbName)
			if dbName == "" {
				continue
			} else if cmutil.StringsHas(SysDBs, dbName) {
				return errors.Errorf("DBListDropIfExists should not contain sys db: %s", dbListDrop)
			} else {
				dblistNew = append(dblistNew, dbName)
			}
		}

		ctx := context.Background()
		dbConn, _ := l.dbConn.Conn(ctx)
		defer dbConn.Close()
		if !l.cnf.LogicalLoad.EnableBinlog {
			if _, err := dbConn.ExecContext(ctx, "set session sql_log_bin=off"); err != nil {
				return errors.WithMessage(err, "disable log_bin for LogicalLoad connection")
			}
		}
		if l.cnf.LogicalLoad.InitCommand != "" {
			if _, err := dbConn.ExecContext(ctx, l.cnf.LogicalLoad.InitCommand); err != nil {
				return errors.WithMessage(err, "init command for LogicalLoad connection")
			}
		}
		for _, dbName := range dblistNew {
			dropDbSql := fmt.Sprintf("DROP DATABASE IF EXISTS `%s`", dbName)
			logger.Log.Warn("DBListDropIfExists sql:", dropDbSql)
			if _, err := dbConn.ExecContext(ctx, dropDbSql); err != nil {
				return errors.Wrap(err, "DBListDropIfExists err")
			}
		}
		return nil
	}
	return nil
}

// Execute execute loading backup with logical load tool [mysql]
// for the mysqldump backup, we use mysql to load it
func (l *LogicalLoaderMysqldump) Execute() (err error) {
	cnfPublic := config.Public{
		MysqlHost:    l.cnf.LogicalLoad.MysqlHost,
		MysqlPort:    l.cnf.LogicalLoad.MysqlPort,
		MysqlUser:    l.cnf.LogicalLoad.MysqlUser,
		MysqlPasswd:  l.cnf.LogicalLoad.MysqlPasswd,
		MysqlCharset: l.cnf.LogicalLoad.MysqlCharset,
	}
	l.dbConn, err = mysqlconn.InitConn(&cnfPublic)
	if err != nil {
		return err
	}
	defer func() {
		_ = l.dbConn.Close()
	}()
	if err = l.preExecute(); err != nil {
		return err
	}

	defer func() {
		if l.initConnect != "" {
			logger.Log.Info("set global init_connect back:", l.initConnect)
			if _, err = l.dbConn.Exec(fmt.Sprintf(`set global init_connect="%s"`, l.initConnect)); err != nil {
				//return err
				logger.Log.Warn("fail set global init_connect back:", l.initConnect)
			}
		}
	}()

	var binPath string
	if l.cnf.LogicalLoadMysqldump.BinPath != "" {
		binPath = l.cnf.LogicalLoadMysqldump.BinPath
	} else {
		binPath = filepath.Join(l.dbbackupHome, "/bin/mysql")
		if !cmutil.FileExists(binPath) {
			binPath, err = exec.LookPath("mysql")
			if err != nil {
				return err
			}
		}
	}

	args := []string{
		"-h" + l.cnf.LogicalLoad.MysqlHost,
		"-P" + strconv.Itoa(l.cnf.LogicalLoad.MysqlPort),
		"-u" + l.cnf.LogicalLoad.MysqlUser,
		"-p" + l.cnf.LogicalLoad.MysqlPasswd,
		"--max_allowed_packet=1073741824 ",
		fmt.Sprintf("--default-character-set=%s", l.cnf.LogicalLoad.MysqlCharset),
	}
	var initCommand []string
	if !l.cnf.LogicalLoad.EnableBinlog {
		initCommand = append(initCommand, "set session sql_log_bin=off")
	}
	if l.cnf.LogicalLoad.InitCommand != "" {
		initCommand = append(initCommand, l.cnf.LogicalLoad.InitCommand)
	}
	if len(initCommand) > 0 {
		args = append(args, fmt.Sprintf(`--init-command='%s'`, strings.Join(initCommand, ";")))
	}

	// ExtraOpt is to freely add command line arguments
	if l.cnf.LogicalLoadMysqldump.ExtraOpt != "" {
		args = append(args, []string{
			fmt.Sprintf(`%s`, l.cnf.LogicalLoadMysqldump.ExtraOpt),
		}...)
	}

	sqlFiles, err := filepath.Glob(filepath.Join(l.cnf.LogicalLoad.MysqlLoadDir, "*_logical.sql"))
	if err != nil {
		return errors.WithMessagef(err, "get sql file from %s", l.cnf.LogicalLoad.MysqlLoadDir)
	} else if len(sqlFiles) == 0 {
		return errors.WithMessagef(err, "no sql file found from %s", l.cnf.LogicalLoad.MysqlLoadDir)
	} else {
		logger.Log.Info("found sql files:", sqlFiles)
	}
	// 取第一个
	dumpedSqlFile := sqlFiles[0]
	args = append(args, "<", dumpedSqlFile)

	pwd, _ := os.Getwd()
	logfile := filepath.Join(pwd, "logs", fmt.Sprintf("mysqldump_load_%d.log", int(time.Now().Weekday())))
	_ = os.MkdirAll(filepath.Dir(logfile), 0755)

	args = append(args, ">>", logfile, "2>&1")
	logger.Log.Info("load logical command:", binPath+" ", strings.Join(args, " "))

	outStr, errStr, err := cmutil.ExecCommand(true, "", binPath, args...)
	if err != nil {
		logger.Log.Error("mysqldump load backup failed: ", err, errStr)
		// 尝试读取 mysqldump_load.log 里 CRITICAL 关键字
		grepError := []string{"grep", "-E", "ERROR", logfile, "|", "tail", "-5"}
		errStrPrefix := fmt.Sprintf("tail 5 error from %s", logfile)
		errStrDetail, _, _ := cmutil.ExecCommand(true, "", grepError[0], grepError[1:]...)
		if len(strings.TrimSpace(errStr)) > 0 {
			logger.Log.Info(errStrPrefix)
			logger.Log.Error(errStrDetail)
		} else {
			logger.Log.Warn("can not find more detail error message from ", logfile)
		}
		return errors.WithMessagef(err, fmt.Sprintf("%s: %s\n%s", errStr, errStrPrefix, errStrDetail))
	}
	logger.Log.Info("load backup success: ", outStr)
	return nil
}
