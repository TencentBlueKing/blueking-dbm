package backupexe

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"github.com/pkg/errors"
)

// PhysicalLoader this is used to load physical backup
type PhysicalLoader struct {
	cnf           *parsecnf.Cnf
	dbbackupHome  string
	mysqlVersion  string
	storageEngine string
	innodbCmd     InnodbCommand
}

func (p *PhysicalLoader) initConfig(indexContent *IndexContent) error {
	if p.cnf == nil {
		return errors.New("physical loader params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		p.dbbackupHome = filepath.Dir(cmdPath)
	}

	p.mysqlVersion = util.VersionParser(indexContent.MysqlVersion)
	p.storageEngine = strings.ToLower(indexContent.StorageEngine)
	p.innodbCmd.ChooseXtrabackupTool(p.mysqlVersion)
	return nil
}

// createPhysicalLoadInnodbCmd Create PhysicalBackup Cmd(Innodb)
func (p *PhysicalLoader) createPhysicalLoadInnodbCmd() (string, error) {
	var buffer bytes.Buffer
	binpath := filepath.Join(p.dbbackupHome, "/bin/xtrabackup", p.innodbCmd.innobackupexBin)
	binpath2 := filepath.Join(p.dbbackupHome, "/bin/xtrabackup", p.innodbCmd.xtrabackupBin)
	buffer.WriteString(binpath)
	buffer.WriteString(" --defaults-file=" + p.cnf.PhysicalLoad.DefaultsFile)
	buffer.WriteString(" --ibbackup=" + binpath2)
	if p.cnf.PhysicalLoad.CopyBack {
		buffer.WriteString(" --copy-back")
	} else {
		buffer.WriteString(" --move-back")
	}
	if p.cnf.PhysicalLoad.ExtraOpt != "" {
		buffer.WriteString(fmt.Sprintf(` %s `, p.cnf.PhysicalLoad.ExtraOpt))
	}
	// targetPath := filepath.Join(cnf.Public.BackupDir, TargetName)
	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		buffer.WriteString(" " + p.cnf.PhysicalLoad.MysqlLoadDir)
	} else {
		buffer.WriteString(" --target-dir=" + p.cnf.PhysicalLoad.MysqlLoadDir)
	}

	cmdStr := buffer.String()
	logger.Log.Info(fmt.Sprintf("load physical backup cmd: %s", cmdStr))
	return cmdStr, nil
}

// createDecompressInnodbCmd create decompress cmd
func (p *PhysicalLoader) createDecompressInnodbCmd() (string, error) {
	var buffer bytes.Buffer
	binpath := filepath.Join(p.dbbackupHome, "/bin/xtrabackup", p.innodbCmd.innobackupexBin)
	buffer.WriteString(binpath)
	buffer.WriteString(" --decompress")
	buffer.WriteString(" --qpress=" + filepath.Join(p.dbbackupHome, "/bin/xtrabackup", "qpress"))
	buffer.WriteString(" --parallel=" + strconv.Itoa(p.cnf.PhysicalLoad.Threads))
	// targetPath := filepath.Join(cnf.Public.BackupDir, TargetName)
	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		buffer.WriteString(" " + p.cnf.PhysicalLoad.MysqlLoadDir)
	} else {
		buffer.WriteString(" --target-dir=" + p.cnf.PhysicalLoad.MysqlLoadDir)
	}
	cmdStr := buffer.String()
	logger.Log.Info(fmt.Sprintf("decompress cmd: %s", cmdStr))
	return cmdStr, nil
}

// createApplyInnodbCmd Create ApplyInnodb Cmd
func (p *PhysicalLoader) createApplyInnodbCmd() (string, error) {
	var buffer bytes.Buffer
	binpath := filepath.Join(p.dbbackupHome, "/bin/xtrabackup", p.innodbCmd.innobackupexBin)
	binpath2 := filepath.Join(p.dbbackupHome, "/bin/xtrabackup", p.innodbCmd.xtrabackupBin)
	buffer.WriteString(binpath)
	buffer.WriteString(" --parallel=" + strconv.Itoa(p.cnf.PhysicalLoad.Threads))
	buffer.WriteString(" --ibbackup=" + binpath2)
	buffer.WriteString(" --use-memory=1GB")
	// targetPath := filepath.Join(cnf.Public.BackupDir, TargetName)
	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		buffer.WriteString(" --apply-log")
	} else {
		buffer.WriteString(" --prepare")
	}
	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		buffer.WriteString(" " + p.cnf.PhysicalLoad.MysqlLoadDir)
	} else {
		buffer.WriteString(" --target-dir=" + p.cnf.PhysicalLoad.MysqlLoadDir)
	}
	cmdStr := buffer.String()
	logger.Log.Info(fmt.Sprintf("apply-log cmd: %s", cmdStr))
	return cmdStr, nil
}

// ExecuteInnodbLoader TODO
func (p *PhysicalLoader) ExecuteInnodbLoader() error {
	var cmdStr string
	var err error
	if cmdStr, err = p.createDecompressInnodbCmd(); err != nil {
		logger.Log.Error("Failed to create the cmd_line of loading backup, error: ", err)
		return err
	}
	if err := util.ExeCommand(cmdStr); err != nil {
		return err
	}

	if cmdStr, err = p.createApplyInnodbCmd(); err != nil {
		logger.Log.Error("Failed to create the cmd_line of loading backup, error: ", err)
		return err
	}
	if err = util.ExeCommand(cmdStr); err != nil {
		return err
	}

	if cmdStr, err = p.createPhysicalLoadInnodbCmd(); err != nil {
		logger.Log.Error("Failed to create the cmd_line of loading backup, error: ", err)
		return err
	}
	if err = util.ExeCommand(cmdStr); err != nil {
		return err
	}
	return nil
}

// Execute execute multiple commands to load physicalbackup
func (p *PhysicalLoader) Execute() error {
	if p.storageEngine == "innodb" {
		err := p.ExecuteInnodbLoader()
		if err != nil {
			logger.Log.Error("Failed to create the cmd_line of laoding backup, error: ", err)
			return err
		}
	} else {
		logger.Log.Error(fmt.Sprintf("This is a unknown StorageEngine: %s", p.storageEngine))
		err := fmt.Errorf("unknown StorageEngine: %s", p.storageEngine)
		return err
	}
	return nil
}
