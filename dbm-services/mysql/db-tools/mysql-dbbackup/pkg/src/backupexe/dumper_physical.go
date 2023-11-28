package backupexe

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// PhysicalDumper TODO
type PhysicalDumper struct {
	cnf           *config.BackupConfig
	dbbackupHome  string
	mysqlVersion  string // parsed
	isOfficial    bool
	innodbCmd     InnodbCommand
	storageEngine string
}

func (p *PhysicalDumper) initConfig(mysqlVerStr string) error {
	if p.cnf == nil {
		return errors.New("logical dumper params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		p.dbbackupHome = filepath.Dir(cmdPath)
	}
	db, err := mysqlconn.InitConn(&p.cnf.Public)
	if err != nil {
		return err
	}
	defer func() {
		_ = db.Close()
	}()
	p.mysqlVersion, p.isOfficial = util.VersionParser(mysqlVerStr)
	p.storageEngine, err = mysqlconn.GetStorageEngine(db)
	if err != nil {
		return err
	}
	p.storageEngine = strings.ToLower(p.storageEngine)

	if err := p.innodbCmd.ChooseXtrabackupTool(p.mysqlVersion, p.isOfficial); err != nil {
		return err
	}

	return nil
}

// Execute excute dumping backup with physical backup tool
func (p *PhysicalDumper) Execute(enableTimeOut bool) error {
	if p.storageEngine != "innodb" {
		err := fmt.Errorf("%s engine not support", p.storageEngine)
		logger.Log.Error(err.Error())
		return err
	}

	binPath := filepath.Join(p.dbbackupHome, p.innodbCmd.innobackupexBin)
	args := []string{
		fmt.Sprintf("--defaults-file=%s", p.cnf.PhysicalBackup.DefaultsFile),
		fmt.Sprintf("--host=%s", p.cnf.Public.MysqlHost),
		fmt.Sprintf("--port=%d", p.cnf.Public.MysqlPort),
		fmt.Sprintf("--user=%s", p.cnf.Public.MysqlUser),
		fmt.Sprintf("--password=%s", p.cnf.Public.MysqlPasswd),
		fmt.Sprintf(
			"--ibbackup=%s", filepath.Join(p.dbbackupHome, p.innodbCmd.xtrabackupBin)),
		"--no-timestamp",
		"--compress",
		"--lazy-backup-non-innodb",
		"--wait-last-flush=2",
	}

	targetPath := filepath.Join(p.cnf.Public.BackupDir, p.cnf.Public.TargetName())
	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		args = append(args, targetPath)
	} else {
		args = append(args, []string{
			fmt.Sprintf("--target-dir=%s", targetPath),
			"--backup", "--binlog-info=ON",
		}...)
	}

	if p.cnf.PhysicalBackup.Threads > 0 {
		args = append(args, []string{
			fmt.Sprintf("--compress-threads=%d", p.cnf.PhysicalBackup.Threads),
			fmt.Sprintf("--parallel=%d", p.cnf.PhysicalBackup.Threads),
		}...)
	}

	if p.cnf.PhysicalBackup.Throttle > 0 {
		args = append(args, []string{
			fmt.Sprintf("--throttle=%d", p.cnf.PhysicalBackup.Throttle),
		}...)
	}

	if strings.ToLower(p.cnf.Public.MysqlRole) == cst.RoleSlave {
		args = append(args, []string{
			"--slave-info", "--safe-slave-backup",
		}...)
	}

	if strings.Compare(p.mysqlVersion, "008000000") >= 0 && p.isOfficial {
		args = append(args, "--skip-strict")
	}

	// ToDo extropt

	var cmd *exec.Cmd
	if enableTimeOut {
		timeDiffUnix, err := GetMaxRunningTime(p.cnf.Public.BackupTimeOut)
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

	outFile, err := os.Create(
		filepath.Join(
			p.dbbackupHome,
			"logs",
			fmt.Sprintf("xtrabackup_%d.log", int(time.Now().Weekday()))))
	if err != nil {
		logger.Log.Error("create log file failed: ", err)
		return err
	}
	defer func() {
		_ = outFile.Close()
	}()

	cmd.Stdout = outFile
	cmd.Stderr = outFile

	logger.Log.Info("xtrabackup command: ", cmd.String())

	err = cmd.Run()
	if err != nil {
		logger.Log.Error("run physical backup failed: ", err)
		return err
	}

	return nil
}
