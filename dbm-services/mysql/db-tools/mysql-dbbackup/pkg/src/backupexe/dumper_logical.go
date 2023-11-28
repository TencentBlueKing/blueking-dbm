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

func (l *LogicalDumper) initConfig(mysqlVerStr string) error {
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
