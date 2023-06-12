package backupexe

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"

	"github.com/spf13/cast"
)

// LogicalDumper TODO
type LogicalDumper struct {
	cnf          *parsecnf.Cnf
	dbbackupHome string
}

func (l *LogicalDumper) initConfig() error {
	if l.cnf == nil {
		return errors.New("logical dumper params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		l.dbbackupHome = filepath.Dir(cmdPath)
	}

	return nil
}

// CreateDumpCmd Create LogicalBackup Cmd
func (l *LogicalDumper) CreateDumpCmd() (string, error) {
	var buffer bytes.Buffer
	binpath := filepath.Join(l.dbbackupHome, "/bin/mydumper")
	buffer.WriteString(binpath)
	buffer.WriteString(" -h " + l.cnf.Public.MysqlHost)
	buffer.WriteString(" -P " + l.cnf.Public.MysqlPort)
	buffer.WriteString(" -u " + l.cnf.Public.MysqlUser)
	buffer.WriteString(" -p " + l.cnf.Public.MysqlPasswd)
	buffer.WriteString(" -o " + l.cnf.Public.BackupDir + "/" + common.TargetName)
	if !l.cnf.LogicalBackup.DisableCompress {
		buffer.WriteString(" --compress")
	}
	if l.cnf.LogicalBackup.DefaultsFile != "" {
		buffer.WriteString(" --defaults-file " + l.cnf.LogicalBackup.DefaultsFile)
	}
	buffer.WriteString(" --trx-consistency-only")
	buffer.WriteString(" --long-query-retries " + cast.ToString(l.cnf.LogicalBackup.FlushRetryCount))
	buffer.WriteString(" --set-names " + l.cnf.Public.MysqlCharset)
	buffer.WriteString(" --chunk-filesize " + cast.ToString(l.cnf.LogicalBackup.ChunkFilesize))
	buffer.WriteString(" --long-query-retry-interval 10")
	// buffer.WriteString(" --checksum-all")
	if l.cnf.LogicalBackup.Regex != "" {
		buffer.WriteString(fmt.Sprintf(` -x '%s'`, l.cnf.LogicalBackup.Regex))
	}
	if common.BackupSchema && !common.BackupData { // backup schema only
		buffer.WriteString(" --no-data")
		buffer.WriteString(" --events --routines --triggers")
	} else if !common.BackupSchema && common.BackupData { // backup data only
		buffer.WriteString(" --no-schemas --no-views")
	} else if common.BackupSchema && common.BackupData { // all
		buffer.WriteString(" --events --routines --triggers")
	}
	buffer.WriteString(" --threads " + strconv.Itoa(l.cnf.LogicalBackup.Threads))
	buffer.WriteString(" " + l.cnf.LogicalBackup.ExtraOpt)
	buffer.WriteString(" > logs/mydumper_`date +%w`.log 2>&1")

	cmdStr := buffer.String()
	logger.Log.Info(fmt.Sprintf("build backup cmd_line: %s", cmdStr))
	return cmdStr, nil
}

// Execute Execute logical dump command
func (l *LogicalDumper) Execute(enableTimeOut bool) error {
	cmdStr, err := l.CreateDumpCmd()
	if err != nil {
		logger.Log.Error("Failed to create the cmd_line of dumping backup, error: ", err)
		return err
	}

	if enableTimeOut {
		timeDiffUinx, err := GetMaxRunningTime(l.cnf.Public.BackupTimeOut)
		if err != nil {
			return err
		}
		ctx, cancel := context.WithTimeout(context.Background(), (time.Duration(timeDiffUinx))*time.Second)
		defer cancel()

		// execute command with timeout
		res, exeErr := exec.CommandContext(ctx, "/bin/bash", "-c", cmdStr).CombinedOutput()
		logger.Log.Info("execute dumping logical backup with timeout, result:", string(res))
		if exeErr != nil {
			logger.Log.Error("Failed to execute dumping logical backup, error:", exeErr)
			return exeErr
		}
	} else {
		res, exeErr := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
		logger.Log.Info("execute dumping logical backup without timeout, result:", string(res))
		if exeErr != nil {
			logger.Log.Error("Failed to execute dumping logical backup, error:", exeErr)
			return exeErr
		}
	}
	return nil
}
