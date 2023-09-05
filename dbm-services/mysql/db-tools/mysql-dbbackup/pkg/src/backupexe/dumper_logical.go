package backupexe

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// LogicalDumper TODO
type LogicalDumper struct {
	cnf          *config.BackupConfig
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
//func (l *LogicalDumper) CreateDumpCmd() (string, error) {
//var buffer bytes.Buffer
//binpath := filepath.Join(l.dbbackupHome, "/bin/mydumper")
//buffer.WriteString(binpath)
//buffer.WriteString(" -h " + l.cnf.Public.MysqlHost)
//buffer.WriteString(" -P " + l.cnf.Public.MysqlPort)
//buffer.WriteString(" -u " + l.cnf.Public.MysqlUser)
//buffer.WriteString(" -p " + l.cnf.Public.MysqlPasswd)
//buffer.WriteString(" -o " + l.cnf.Public.BackupDir + "/" + common.TargetName)
//if !l.cnf.LogicalBackup.DisableCompress {
//	buffer.WriteString(" --compress")
//}
//if l.cnf.LogicalBackup.DefaultsFile != "" {
//	buffer.WriteString(" --defaults-file " + l.cnf.LogicalBackup.DefaultsFile)
//}
//buffer.WriteString(" --trx-consistency-only")
//buffer.WriteString(" --long-query-retries " + cast.ToString(l.cnf.LogicalBackup.FlushRetryCount))
//buffer.WriteString(" --set-names " + l.cnf.Public.MysqlCharset)
//buffer.WriteString(" --chunk-filesize " + cast.ToString(l.cnf.LogicalBackup.ChunkFileSize))
//buffer.WriteString(" --long-query-retry-interval 10")
// -- buffer.WriteString(" --checksum-all")
//if l.cnf.LogicalBackup.Regex != "" {
//	buffer.WriteString(fmt.Sprintf(` -x '%s'`, l.cnf.LogicalBackup.Regex))
//}
//if common.BackupSchema && !common.BackupData { // backup schema only
//	buffer.WriteString(" --no-data")
//	buffer.WriteString(" --events --routines --triggers")
//} else if !common.BackupSchema && common.BackupData { // backup data only
//	buffer.WriteString(" --no-schemas --no-views")
//} else if common.BackupSchema && common.BackupData { // all
//	buffer.WriteString(" --events --routines --triggers")
//}
//buffer.WriteString(" --threads " + strconv.Itoa(l.cnf.LogicalBackup.Threads))
//	buffer.WriteString(" " + l.cnf.LogicalBackup.ExtraOpt)
//	buffer.WriteString(" > logs/mydumper_`date +%w`.log 2>&1")
//
//	cmdStr := buffer.String()
//	logger.Log.Info(fmt.Sprintf("build backup cmd_line: %s", cmdStr))
//	return cmdStr, nil
//}

//// Execute Execute logical dump command
//func (l *LogicalDumper) Execute(enableTimeOut bool) error {
//	cmdStr, err := l.CreateDumpCmd()
//	if err != nil {
//		logger.Log.Error("Failed to create the cmd_line of dumping backup, error: ", err)
//		return err
//	}
//
//	if enableTimeOut {
//		timeDiffUnix, err := GetMaxRunningTime(l.cnf.Public.BackupTimeOut)
//		if err != nil {
//			return err
//		}
//		ctx, cancel := context.WithTimeout(context.Background(), (time.Duration(timeDiffUnix))*time.Second)
//		defer cancel()
//
//		// execute command with timeout
//		res, exeErr := exec.CommandContext(ctx, "/bin/bash", "-c", cmdStr).CombinedOutput()
//		logger.Log.Info("execute dumping logical backup with timeout, result:", string(res))
//		if exeErr != nil {
//			logger.Log.Error("Failed to execute dumping logical backup, error:", exeErr)
//			return exeErr
//		}
//	} else {
//		res, exeErr := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
//		logger.Log.Info("execute dumping logical backup without timeout, result:", string(res))
//		if exeErr != nil {
//			logger.Log.Error("Failed to execute dumping logical backup, error:", exeErr)
//			return exeErr
//		}
//	}
//	return nil
//}

// Execute excute dumping backup with logical backup tool
func (l *LogicalDumper) Execute(enableTimeOut bool) error {
	binPath := filepath.Join(l.dbbackupHome, "/bin/mydumper")
	args := []string{
		"-h", l.cnf.Public.MysqlHost,
		"-P", strconv.Itoa(l.cnf.Public.MysqlPort),
		"-u", l.cnf.Public.MysqlUser,
		"-p", l.cnf.Public.MysqlPasswd,
		"-o", filepath.Join(l.cnf.Public.BackupDir, l.cnf.Public.TargetName()),
		fmt.Sprintf("--long-query-retries=%d", l.cnf.LogicalBackup.FlushRetryCount),
		fmt.Sprintf("--set-names=%s", l.cnf.Public.MysqlCharset),
		fmt.Sprintf("--chunk-filesize=%d", l.cnf.LogicalBackup.ChunkFilesize),
		fmt.Sprintf("--threads=%d", l.cnf.LogicalBackup.Threads),
		"--trx-consistency-only",
		"--long-query-retry-interval=10",
	}

	if !l.cnf.LogicalBackup.DisableCompress {
		args = append(args, "--compress")
	}
	if l.cnf.LogicalBackup.DefaultsFile != "" {
		args = append(args, []string{
			fmt.Sprintf("--defaults-file=%s", l.cnf.LogicalBackup.DefaultsFile),
		}...)
	}
	if l.cnf.LogicalBackup.Regex != "" {
		args = append(args, []string{
			"-x", fmt.Sprintf(`'%s'`, l.cnf.LogicalBackup.Regex),
		}...)
	}
	if l.cnf.Public.IfBackupSchema() && !l.cnf.Public.IfBackupData() {
		args = append(args, []string{
			"--no-data", "--events", "--routines", "--triggers",
		}...)
	} else if !l.cnf.Public.IfBackupSchema() && l.cnf.Public.IfBackupData() {
		args = append(args, []string{
			"--no-schemas", "--no-views",
		}...)
	} else if l.cnf.Public.IfBackupSchema() && l.cnf.Public.IfBackupData() {
		args = append(args, []string{
			"--events", "--routines", "--triggers",
		}...)
	}

	// ToDo extropt

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

	logger.Log.Info("logical dump command: ", cmd.String())

	outFile, err := os.Create(
		filepath.Join(
			l.dbbackupHome,
			"logs",
			fmt.Sprintf("mydumper_%d.log", int(time.Now().Weekday()))))
	if err != nil {
		logger.Log.Error("create log file failed: ", err)
		return err
	}
	defer func() {
		_ = outFile.Close()
	}()

	cmd.Stdout = outFile
	cmd.Stderr = outFile

	err = cmd.Run()
	if err != nil {
		logger.Log.Error("run logical backup failed: ", err)
		return err
	}

	return nil
}
