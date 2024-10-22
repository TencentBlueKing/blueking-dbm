package backupexe

import (
	"context"
	"database/sql"
	"fmt"
	"os"
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

// LogicalLoader this is used to load logical backup
type LogicalLoader struct {
	cnf                 *config.BackupConfig
	dbbackupHome        string
	dbConn              *sql.DB
	initConnectOriginal string
	metaInfo            *dbareport.IndexContent
}

func (l *LogicalLoader) initConfig(metaInfo *dbareport.IndexContent) error {
	if l.cnf == nil {
		return errors.New("logical loader params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		l.dbbackupHome = filepath.Dir(cmdPath)
	}
	l.metaInfo = metaInfo
	if l.cnf.LogicalLoad.MysqlCharset == "" {
		l.cnf.LogicalLoad.MysqlCharset = metaInfo.BackupCharset
	}
	return nil
}

func (l *LogicalLoader) preExecute() error {
	// 临时清理 init_connect
	dbListDrop := l.cnf.LogicalLoad.DBListDropIfExists
	var initConnect string
	if err := l.dbConn.QueryRow("select @@init_connect").Scan(&initConnect); err != nil {
		return err
	}
	l.initConnectOriginal = initConnect
	if l.initConnectOriginal != "" && strings.TrimSpace(dbListDrop) != "" {
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

// Execute execute loading backup with logical backup tool
func (l *LogicalLoader) Execute() (err error) {
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
	defer func() {
		if l.initConnectOriginal != "" {
			logger.Log.Info("set global init_connect back:", l.initConnectOriginal)
			if _, err = l.dbConn.Exec(fmt.Sprintf(`set global init_connect="%s"`, l.initConnectOriginal)); err != nil {
				//return err
				logger.Log.Warn("fail set global init_connect back:", l.initConnectOriginal)
			}
		}
	}()
	if err = l.preExecute(); err != nil {
		return err
	}
	pwd, _ := os.Getwd()

	binPath := filepath.Join(l.dbbackupHome, "bin/myloader")
	args := []string{
		"-h", l.cnf.LogicalLoad.MysqlHost,
		"-P", strconv.Itoa(l.cnf.LogicalLoad.MysqlPort),
		"-u", l.cnf.LogicalLoad.MysqlUser,
		"-p", l.cnf.LogicalLoad.MysqlPasswd,
		"-d", l.cnf.LogicalLoad.MysqlLoadDir,
		fmt.Sprintf("--set-names=%s", l.cnf.LogicalLoad.MysqlCharset),
	}
	if l.cnf.LogicalLoad.InitCommand != "" {
		// https://github.com/mydumper/mydumper/blob/master/README.md#defaults-file
		// [myloader_session_variables]
		// tc_admin=0  # for tdbctl
		sessionVars, globalVars := SetVariablesToConfigIni(l.cnf.LogicalLoad.InitCommand)
		myloaderVariables := &MydumperIni{
			MyloaderSessionVariables: sessionVars,
			MyloaderGlobalVariables:  globalVars,
		}
		defaultsFile := filepath.Join(pwd, fmt.Sprintf("myloader_vars_%d.cnf", l.cnf.LogicalLoad.MysqlPort))
		if err = myloaderVariables.SaveIni(defaultsFile); err != nil {
			return errors.WithMessage(err, "generate myloader_vars")
		}
		args = append(args, "--defaults-file", defaultsFile)
	}
	var serverVersion string
	if err := l.dbConn.QueryRow("select version()").Scan(&serverVersion); err == nil {
		if strings.Contains(serverVersion, "tdbctl") &&
			!strings.Contains(strings.ToLower(l.cnf.LogicalLoad.InitCommand), "tc_admin") {
			return errors.Errorf("importing sql to tdbctl need setting tc_admin as InitCommand")
		}
	}
	if l.cnf.LogicalLoad.Threads > 0 {
		// cpus, err := cmutil.GetCPUInfo()
		args = append(args, fmt.Sprintf("--threads=%d", l.cnf.LogicalLoad.Threads))
	}
	if l.cnf.LogicalLoad.EnableBinlog {
		args = append(args, "--enable-binlog")
	}
	if l.cnf.LogicalLoad.SchemaOnly {
		args = append(args, "--no-data")
	}
	if l.cnf.LogicalLoad.CreateTableIfNotExists {
		args = append(args, "--append-if-not-exist")
	}
	if tableFilter, err := l.cnf.LogicalLoad.BuildArgsTableFilterForMydumper(); err != nil {
		return err
	} else {
		args = append(args, tableFilter...)
	}
	// ToDo extraOpt
	// myloader 日志输出到当前目录的 logs/myloader_xx.log
	logfile := filepath.Join(pwd, "logs", fmt.Sprintf("myloader_%d.log", int(time.Now().Weekday())))
	_ = os.MkdirAll(filepath.Dir(logfile), 0755)

	args = append(args, ">>", logfile, "2>&1")
	logger.Log.Info("load logical command:", binPath+" ", strings.Join(args, " "))
	outStr, errStr, err := cmutil.ExecCommand(true, "", binPath, args...)
	if err != nil {
		logger.Log.Error("myloader load backup failed: ", err, errStr)
		// 尝试读取 myloader.log 里 CRITICAL 关键字
		grepError := []string{"grep", "-E", "CRITICAL", logfile, "|", "tail", "-5"}
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
