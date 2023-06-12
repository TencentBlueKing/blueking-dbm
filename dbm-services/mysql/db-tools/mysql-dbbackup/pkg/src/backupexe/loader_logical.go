package backupexe

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"

	"github.com/pkg/errors"
)

// LogicalLoader this is used to load logical backup
type LogicalLoader struct {
	cnf          *parsecnf.Cnf
	dbbackupHome string
}

func (l *LogicalLoader) initConfig(indexContent *IndexContent) error {
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

// CreateCommand Create LogicalLoad Cmd
func (l *LogicalLoader) CreateCommand() (string, error) {
	binpath := filepath.Join(l.dbbackupHome, "bin/myloader")
	var buffer bytes.Buffer

	buffer.WriteString(binpath)
	buffer.WriteString(" -h " + l.cnf.LogicalLoad.MysqlHost)
	buffer.WriteString(" -P " + l.cnf.LogicalLoad.MysqlPort)
	buffer.WriteString(" -u " + l.cnf.LogicalLoad.MysqlUser)
	buffer.WriteString(" -p " + l.cnf.LogicalLoad.MysqlPasswd)
	buffer.WriteString(" -d " + l.cnf.LogicalLoad.MysqlLoadDir)
	buffer.WriteString(" --threads " + strconv.Itoa(l.cnf.LogicalLoad.Threads))
	buffer.WriteString(" --set-names " + l.cnf.LogicalLoad.MysqlCharset)
	if l.cnf.LogicalLoad.EnableBinlog {
		buffer.WriteString(" --enable-binlog ")
	}
	if l.cnf.LogicalLoad.Regex != "" {
		buffer.WriteString(fmt.Sprintf(` -x '%s'`, l.cnf.LogicalLoad.Regex))
	}
	if l.cnf.LogicalLoad.ExtraOpt != "" {
		buffer.WriteString(fmt.Sprintf(` %s `, l.cnf.LogicalLoad.ExtraOpt))
	}
	cmdStr := buffer.String()
	logger.Log.Info("logical loader cmd: ", cmdStr)
	return cmdStr, nil
}

// Execute execute myloader command
func (l *LogicalLoader) Execute() error {
	cmdStr, err := l.CreateCommand()
	if err != nil {
		logger.Log.Error("Failed to create the cmd_line of loading backup, error: ", err)
		return err
	}
	res, exeErr := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
	if exeErr != nil {
		logger.Log.Error("Failed to execute loading backup, error: ", exeErr, string(res))
		return errors.Wrap(exeErr, string(res))
	}
	logger.Log.Info("execute loading backup, result: ", string(res))
	return nil
}
