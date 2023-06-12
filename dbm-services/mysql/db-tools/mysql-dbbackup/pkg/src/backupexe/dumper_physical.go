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
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// PhysicalDumper TODO
type PhysicalDumper struct {
	cnf           *parsecnf.Cnf
	dbbackupHome  string
	mysqlVersion  string
	innodbCmd     InnodbCommand
	storageEngine string
}

func (p *PhysicalDumper) initConfig() error {
	if p.cnf == nil {
		return errors.New("logical dumper params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		p.dbbackupHome = filepath.Dir(cmdPath)
	}
	DB, err := mysqlconn.InitConn(&p.cnf.Public)
	if err != nil {
		return err
	}
	defer DB.Close()
	versionStr, verErr := mysqlconn.GetMysqlVersion(DB)
	if verErr != nil {
		return verErr
	}
	p.mysqlVersion = util.VersionParser(versionStr)
	p.storageEngine, err = mysqlconn.GetStorageEngine(DB)
	if err != nil {
		return err
	}
	p.storageEngine = strings.ToLower(p.storageEngine)

	p.innodbCmd.ChooseXtrabackupTool(p.mysqlVersion)

	return nil
}

// CreateDumpCmd Create PhysicalBackup Cmd(Innodb)
func (p *PhysicalDumper) CreateDumpCmd() (string, error) {
	var buffer bytes.Buffer
	binpath := filepath.Join(p.dbbackupHome, "/bin/xtrabackup", p.innodbCmd.innobackupexBin)
	binpath2 := filepath.Join(p.dbbackupHome, "/bin/xtrabackup", p.innodbCmd.xtrabackupBin)
	buffer.WriteString(binpath)
	buffer.WriteString(" --defaults-file=" + p.cnf.PhysicalBackup.DefaultsFile)
	buffer.WriteString(" --host=" + p.cnf.Public.MysqlHost)
	buffer.WriteString(" --port=" + p.cnf.Public.MysqlPort)
	buffer.WriteString(" --user=" + p.cnf.Public.MysqlUser)
	buffer.WriteString(" --password=" + p.cnf.Public.MysqlPasswd)
	buffer.WriteString(" --ibbackup=" + binpath2)
	buffer.WriteString(" --no-timestamp --compress") // --compress=qpress
	targetPath := filepath.Join(p.cnf.Public.BackupDir, common.TargetName)
	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		buffer.WriteString(" " + targetPath)
	} else {
		buffer.WriteString(" --target-dir=" + targetPath + " --backup --binlog-info=ON")
	}
	if p.cnf.PhysicalBackup.Threads > 0 {
		buffer.WriteString(" --compress-thread=" + strconv.Itoa(p.cnf.PhysicalBackup.Threads))
		buffer.WriteString(" --parallel=" + strconv.Itoa(p.cnf.PhysicalBackup.Threads))
	}
	if p.cnf.PhysicalBackup.Throttle > 0 {
		buffer.WriteString(" --throttle=" + strconv.Itoa(p.cnf.PhysicalBackup.Throttle))
	}
	buffer.WriteString(" --lazy-backup-non-innodb --wait-last-flush=2")
	if strings.ToLower(p.cnf.Public.MysqlRole) == cst.RoleSlave {
		buffer.WriteString(" --slave-info --safe-slave-backup")
	}
	buffer.WriteString(" " + p.cnf.PhysicalBackup.ExtraOpt)
	buffer.WriteString(" > logs/xtrabackup_`date +%w`.log 2>&1")
	cmdStr := buffer.String()
	logger.Log.Info(fmt.Sprintf("build backup cmd_line: %s", cmdStr))
	return cmdStr, nil
}

// Execute Execute physical dump command
func (p *PhysicalDumper) Execute(enableTimeOut bool) error {
	var cmdStr string
	var err error
	if p.storageEngine == "innodb" {
		cmdStr, err = p.CreateDumpCmd()
		if err != nil {
			logger.Log.Error("Failed to create the cmd_line of dumping backup, error: ", err)
			return err
		}
	} else {
		logger.Log.Error(fmt.Sprintf("This is a unknown StorageEngine: %s", p.storageEngine))
		err := fmt.Errorf("unknown StorageEngine: %s", p.storageEngine)
		return err
	}

	if enableTimeOut {
		timeDiffUinx, err := GetMaxRunningTime(p.cnf.Public.BackupTimeOut)
		if err != nil {
			return err
		}
		ctx, cancel := context.WithTimeout(context.Background(), (time.Duration(timeDiffUinx))*time.Second)
		defer cancel()

		// execute command with timeout
		res, exeErr := exec.CommandContext(ctx, "/bin/bash", "-c", cmdStr).CombinedOutput()
		logger.Log.Info("execute dumping physical backup with timeout, result:", string(res))
		if exeErr != nil {
			logger.Log.Error("Failed to execute dumping physical backup, error: ", exeErr)
			return exeErr
		}
	} else {
		res, exeErr := exec.Command("/bin/bash", "-c", cmdStr).CombinedOutput()
		logger.Log.Info("execute dumping physical backup without timeout, result:", string(res))
		if exeErr != nil {
			logger.Log.Error("Failed to execute dumping physical backup, error: ", exeErr)
			return exeErr
		}
	}
	return nil
}
