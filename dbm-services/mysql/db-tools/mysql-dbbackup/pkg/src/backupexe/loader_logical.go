package backupexe

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// LogicalLoader this is used to load logical backup
type LogicalLoader struct {
	cnf          *config.BackupConfig
	dbbackupHome string
}

func (l *LogicalLoader) initConfig(_ *IndexContent) error {
	if l.cnf == nil {
		return errors.New("logical loader params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		l.dbbackupHome = filepath.Dir(cmdPath)
	}

	return nil
}

// Execute execute loading backup with logical backup tool
func (l *LogicalLoader) Execute() error {
	binPath := filepath.Join(l.dbbackupHome, "bin/myloader")
	args := []string{
		"-h", l.cnf.LogicalLoad.MysqlHost,
		"-P", strconv.Itoa(l.cnf.LogicalLoad.MysqlPort),
		"-u", l.cnf.LogicalLoad.MysqlUser,
		"-p", l.cnf.LogicalLoad.MysqlPasswd,
		"-d", l.cnf.LogicalLoad.MysqlLoadDir,
		fmt.Sprintf("--threads=%d", l.cnf.LogicalLoad.Threads),
		fmt.Sprintf("--set-names=%s", l.cnf.LogicalLoad.MysqlCharset),
	}
	if l.cnf.LogicalLoad.EnableBinlog {
		args = append(args, "--enable-binlog")
	}
	if l.cnf.LogicalLoad.SchemaOnly {
		args = append(args, "--no-data")
	}
	if l.cnf.LogicalLoad.Regex != "" {
		args = append(args, "-x", fmt.Sprintf(`'%s'`, l.cnf.LogicalLoad.Regex))
	}
	// ToDo extraOpt
	// myloader 日志输出到当前目录的 logs/myloader_xx.log
	pwd, _ := os.Getwd()
	logfile := filepath.Join(pwd, "logs", fmt.Sprintf("myloader_%d.log", int(time.Now().Weekday())))
	_ = os.MkdirAll(filepath.Dir(logfile), 0755)

	args = append(args, ">>", logfile, "2>&1")
	logger.Log.Info("load logical command:", binPath, strings.Join(args, " "))
	outStr, errStr, err := cmutil.ExecCommand(true, "", binPath, args...)
	if err != nil {
		logger.Log.Error("load backup failed: ", err, errStr)
		return errors.Wrap(err, errStr)
	}
	logger.Log.Info("load backup success: ", outStr)
	return nil
}
