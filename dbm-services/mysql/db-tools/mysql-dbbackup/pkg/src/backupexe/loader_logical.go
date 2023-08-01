package backupexe

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

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

//// CreateCommand Create LogicalLoad Cmd
//func (l *LogicalLoader) CreateCommand() (string, error) {
//	binPath := filepath.Join(l.dbbackupHome, "bin/myloader")
//	var buffer bytes.Buffer
//
//	buffer.WriteString(binPath)
//	buffer.WriteString(" -h " + l.cnf.LogicalLoad.MysqlHost)
//	buffer.WriteString(" -P " + l.cnf.LogicalLoad.MysqlPort)
//	buffer.WriteString(" -u " + l.cnf.LogicalLoad.MysqlUser)
//	buffer.WriteString(" -p " + l.cnf.LogicalLoad.MysqlPasswd)
//	buffer.WriteString(" -d " + l.cnf.LogicalLoad.MysqlLoadDir)
//	buffer.WriteString(" --threads " + strconv.Itoa(l.cnf.LogicalLoad.Threads))
//	buffer.WriteString(" --set-names " + l.cnf.LogicalLoad.MysqlCharset)
//	if l.cnf.LogicalLoad.EnableBinlog {
//		buffer.WriteString(" --enable-binlog ")
//	}
//	if l.cnf.LogicalLoad.Regex != "" {
//		buffer.WriteString(fmt.Sprintf(` -x '%s'`, l.cnf.LogicalLoad.Regex))
//	}
//	if l.cnf.LogicalLoad.ExtraOpt != "" {
//		buffer.WriteString(fmt.Sprintf(` %s `, l.cnf.LogicalLoad.ExtraOpt))
//	}
//	cmdStr := buffer.String()
//	logger.Log.Info("logical loader cmd: ", cmdStr)
//	return cmdStr, nil
//}
//
//// Execute execute myloader command
//func (l *LogicalLoader) Execute() error {
//	cmdStr, err := l.CreateCommand()
//	if err != nil {
//		logger.Log.Error("Failed to create the cmd_line of loading backup, error: ", err)
//		return err
//	}
//	res, exeErr := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
//	if exeErr != nil {
//		logger.Log.Error("Failed to execute loading backup, error: ", exeErr, string(res))
//		return errors.Wrap(exeErr, string(res))
//	}
//	logger.Log.Info("execute loading backup, result: ", string(res))
//	return nil
//}

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
	if l.cnf.LogicalLoad.Regex != "" {
		args = append(args, []string{
			"-x", fmt.Sprintf(`'%s'`, l.cnf.LogicalLoad.Regex),
		}...)
	}
	// ToDo extraOpt

	args = append(args, ">", "logs/")
	cmutil.ExecCommand(true, "", binPath, args...)

	cmd := exec.Command("sh", "-c",
		fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " ")))

	logger.Log.Info("load logical command: ", cmd.String())

	output, err := cmd.CombinedOutput()
	if err != nil {
		logger.Log.Error("load backup failed: ", err, string(output))
		return errors.Wrap(err, string(output))
	}

	logger.Log.Info("load backup success: ", string(output))
	return nil
}
