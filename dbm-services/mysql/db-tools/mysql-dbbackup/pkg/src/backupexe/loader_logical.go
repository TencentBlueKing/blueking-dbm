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
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/db_table_filter"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
)

// LogicalLoader this is used to load logical backup
type LogicalLoader struct {
	cnf                 *config.LogicalLoad
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
	if l.cnf.MysqlCharset == "" {
		l.cnf.MysqlCharset = metaInfo.BackupCharset
	}
	return nil
}

func (l *LogicalLoader) preExecute() error {
	// 临时清理 init_connect
	dbListDrop := l.cnf.DBListDropIfExists
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
		if err := dropDatabasesBeforeLoad(dbListDrop, l.cnf, l.dbConn); err != nil {
			return err
		}
	}
	return nil
}

func dropDatabasesBeforeLoad(dbListToDropStr string, cnf *config.LogicalLoad, dbConn *sql.DB) error {
	logger.Log.Info("load logical DBListDropIfExists:", dbListToDropStr)
	if strings.Contains(dbListToDropStr, "`") || strings.Contains(dbListToDropStr, ";") {
		return errors.Errorf("DBListDropIfExists has invalid character %s", dbListToDropStr)
	}
	SysDBs := []string{"mysql", "sys", "information_schema", "performance_schema", "test"}

	dbListToDrop := strings.Split(dbListToDropStr, ",")
	dbListToDropNew := []string{}
	for _, dbName := range dbListToDrop {
		dbName = strings.TrimSpace(dbName)
		if dbName == "" {
			continue
		} else if cmutil.StringsHas(SysDBs, dbName) {
			return errors.Errorf("DBListDropIfExists should not contain sys db: %s", dbListToDropStr)
		} else {
			dbListToDropNew = append(dbListToDropNew, dbName)
		}
	}
	dbListToDropFilter, _ := db_table_filter.NewFilter(dbListToDropNew, []string{"*"}, SysDBs, []string{})
	dbListToDropFiltered, err := dbListToDropFilter.GetDbsByConnRaw(dbConn)
	if err != nil {
		return errors.WithMessage(err, "failed to filter db list to drop")
	} else {
		logger.Log.Info("filtered database list to drop:", dbListToDropFiltered)
	}

	ctx := context.Background()
	db, _ := dbConn.Conn(ctx)
	defer dbConn.Close()
	if !cnf.EnableBinlog {
		if _, err := db.ExecContext(ctx, "set session sql_log_bin=off"); err != nil {
			return errors.WithMessage(err, "disable log_bin for LogicalLoad connection")
		}
	}
	if cnf.InitCommand != "" {
		if _, err := db.ExecContext(ctx, cnf.InitCommand); err != nil {
			return errors.WithMessage(err, "init command for LogicalLoad connection")
		}
	}
	for _, dbName := range dbListToDropFiltered {
		dropDbSql := fmt.Sprintf("DROP DATABASE IF EXISTS `%s`", dbName)
		logger.Log.Warn("DBListDropIfExists sql:", dropDbSql)
		if _, err := db.ExecContext(ctx, dropDbSql); err != nil {
			return errors.Wrap(err, "DBListDropIfExists err")
		}
	}
	return nil
}

// Execute execute loading backup with logical backup tool
func (l *LogicalLoader) Execute() (err error) {
	cnfPublic := config.Public{
		MysqlHost:    l.cnf.MysqlHost,
		MysqlPort:    l.cnf.MysqlPort,
		MysqlUser:    l.cnf.MysqlUser,
		MysqlPasswd:  l.cnf.MysqlPasswd,
		MysqlCharset: l.cnf.MysqlCharset,
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
		"-v", strconv.Itoa(3),
		"-h", l.cnf.MysqlHost,
		"-P", strconv.Itoa(l.cnf.MysqlPort),
		"-u", l.cnf.MysqlUser,
		fmt.Sprintf(`-p '%s'`, l.cnf.MysqlPasswd), // 密码里可能有特殊字符
		"-d", l.cnf.MysqlLoadDir,
		fmt.Sprintf("--set-names=%s", l.cnf.MysqlCharset),
	}
	if !strings.Contains(l.cnf.InitCommand, "max_allowed_packet") {
		l.cnf.InitCommand += ";set global max_allowed_packet=1073741824"
	}
	if l.cnf.InitCommand != "" {
		// https://github.com/mydumper/mydumper/blob/master/README.md#defaults-file
		// [myloader_session_variables]
		// tc_admin=0  # for tdbctl
		sessionVars, globalVars := SetVariablesToConfigIni(l.cnf.InitCommand)
		myloaderVariables := &MydumperIni{
			MyloaderSessionVariables: sessionVars,
			MyloaderGlobalVariables:  globalVars,
		}
		defaultsFile := filepath.Join(pwd, fmt.Sprintf("myloader_vars_%d.cnf", l.cnf.MysqlPort))
		if err = myloaderVariables.SaveIni(defaultsFile); err != nil {
			return errors.WithMessage(err, "generate myloader_vars")
		}
		args = append(args, "--defaults-file", defaultsFile)
	}
	var serverVersion string
	if err := l.dbConn.QueryRow("select version()").Scan(&serverVersion); err == nil {
		if strings.Contains(serverVersion, "tdbctl") &&
			!strings.Contains(strings.ToLower(l.cnf.InitCommand), "tc_admin") {
			return errors.Errorf("importing sql to tdbctl need setting tc_admin as InitCommand")
		}
	}
	if l.cnf.Threads > 0 {
		// cpus, err := cmutil.GetCPUInfo()
		args = append(args, fmt.Sprintf("--threads=%d", l.cnf.Threads))
	}
	if l.cnf.EnableBinlog {
		args = append(args, "--enable-binlog")
	}
	if l.cnf.SchemaOnly {
		args = append(args, "--no-data")
	}
	if l.cnf.CreateTableIfNotExists {
		args = append(args, "--append-if-not-exist")
	}
	if tableFilter, err := l.cnf.BuildArgsTableFilterForMydumper(); err != nil {
		return err
	} else {
		args = append(args, tableFilter...)
	}
	// ToDo extraOpt
	// myloader 日志输出到当前目录的 logs/myloader_xx.log
	logfile := filepath.Join(pwd, "logs", fmt.Sprintf("myloader_%d_%d.log",
		l.cnf.MysqlPort, int(time.Now().Weekday())))
	_ = os.MkdirAll(filepath.Dir(logfile), 0755)

	args = append(args, ">>", logfile, "2>&1")
	logger.Log.Info("load logical command:", binPath+" ",
		mysqlcomm.RemoveMysqlCommandPassword(strings.Join(args, " ")))
	outStr, errStr, err := cmutil.ExecCommand(true, "", binPath, args...)
	if err != nil {
		logger.Log.Error("myloader load backup failed: ", err, errStr)
		// 尝试读取 myloader.log 里 CRITICAL 关键字
		errStrPrefix := fmt.Sprintf("head 5 error from %s", logfile)
		errStrDetail, _ := cmutil.NewGrepLines(logfile, true, true).
			MatchWords([]string{"CRITICAL", "not found", "fatal", "No such file"}, 5)
		if len(errStrDetail) > 0 {
			logger.Log.Info(errStrPrefix)
			logger.Log.Error(errStrDetail)
		} else {
			logger.Log.Warn("tail can not find more detail error message from ", logfile)
		}
		return errors.WithMessagef(err, fmt.Sprintf("%s\n%s", errStrPrefix, errStrDetail))
	}
	logger.Log.Info("load backup success: ", outStr)
	return nil
}
