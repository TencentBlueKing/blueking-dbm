package backupexe

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"

	"github.com/pkg/errors"
)

// PhysicalLoader this is used to load physical backup
// decompress, apply, recover
type PhysicalLoader struct {
	cnf           *config.BackupConfig
	dbbackupHome  string
	mysqlVersion  string
	storageEngine string
	innodbCmd     InnodbCommand
	isOfficial    bool
}

func (p *PhysicalLoader) initConfig(indexContent *dbareport.IndexContent) error {
	if p.cnf == nil {
		return errors.New("physical loader params is nil")
	}
	if cmdPath, err := os.Executable(); err != nil {
		return err
	} else {
		p.dbbackupHome = filepath.Dir(cmdPath)
	}

	p.mysqlVersion, p.isOfficial = util.VersionParser(indexContent.MysqlVersion)
	p.storageEngine = strings.ToLower(indexContent.StorageEngine)
	if err := p.innodbCmd.ChooseXtrabackupTool(p.mysqlVersion, p.isOfficial); err != nil {
		return err
	}
	return nil
}

// Execute excute loading backup with physical backup tool
func (p *PhysicalLoader) Execute() error {
	if p.storageEngine != "innodb" {
		err := fmt.Errorf("%s engine not supported", p.storageEngine)
		logger.Log.Error(err)
		return err
	}

	err := p.decompress()
	if err != nil {
		return err
	}

	err = p.apply()
	if err != nil {
		return err
	}

	err = p.load()
	if err != nil {
		return err
	}

	return nil
}

func (p *PhysicalLoader) decompress() error {
	binPath := filepath.Join(p.dbbackupHome, p.innodbCmd.innobackupexBin)

	args := []string{
		"--decompress",
		//fmt.Sprintf("--qpress=%s", filepath.Join(p.dbbackupHome, "/bin", "qpress")),
		fmt.Sprintf("--parallel=%d", p.cnf.PhysicalLoad.Threads),
	}
	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		args = append(args, p.cnf.PhysicalLoad.MysqlLoadDir)
	} else {
		args = append(args, []string{
			fmt.Sprintf("--target-dir=%s", p.cnf.PhysicalLoad.MysqlLoadDir),
		}...)
	}
	if strings.Compare(p.mysqlVersion, "008000000") >= 0 && p.isOfficial {
		args = append(args, "--skip-strict")
	}

	// decompress 日志输出到当前目录的 logs/xtrabackup_xx.log
	pwd, _ := os.Getwd()
	logfile := filepath.Join(pwd, "logs", fmt.Sprintf("xtrabackup_%d.log", int(time.Now().Weekday())))
	_ = os.MkdirAll(filepath.Dir(logfile), 0755)
	// decompress 会把正常日志打印到错误输出
	args = append(args, ">>", logfile, "2>&1")
	logger.Log.Info("decompress command:", binPath, strings.Join(args, " "))
	outStr, errStr, err := cmutil.ExecCommand(true, "", binPath, args...)
	if err != nil {
		logger.Log.Error("decompress failed: ", err, errStr)
		return errors.Wrap(err, errStr)
	}
	logger.Log.Info("decompress success: ", outStr)
	return nil
}

func (p *PhysicalLoader) apply() error {
	binPath := filepath.Join(p.dbbackupHome, p.innodbCmd.innobackupexBin)

	args := []string{
		fmt.Sprintf("--parallel=%d", p.cnf.PhysicalLoad.Threads),
		fmt.Sprintf(
			"--ibbackup=%s", filepath.Join(p.dbbackupHome, p.innodbCmd.xtrabackupBin)),
		"--use-memory=1GB",
	}

	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		args = append(args, "--apply-log")
	} else {
		args = append(args, "--prepare")
	}

	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		args = append(args, p.cnf.PhysicalLoad.MysqlLoadDir)
	} else {
		args = append(args, []string{
			fmt.Sprintf("--target-dir=%s", p.cnf.PhysicalLoad.MysqlLoadDir),
		}...)
	}

	if strings.Compare(p.mysqlVersion, "008000000") >= 0 && p.isOfficial {
		args = append(args, "--skip-strict")
	}

	// apply 日志输出到当前目录的 logs/xtrabackup_xx.log
	pwd, _ := os.Getwd()
	logfile := filepath.Join(pwd, "logs", fmt.Sprintf("xtrabackup_%d.log", int(time.Now().Weekday())))
	_ = os.MkdirAll(filepath.Dir(logfile), 0755)

	args = append(args, ">>", logfile, "2>&1")
	logger.Log.Info("physical apply command:", binPath, strings.Join(args, " "))
	outStr, errStr, err := cmutil.ExecCommand(true, "", binPath, args...)
	if err != nil {
		logger.Log.Error("physical apply failed: ", err, errStr)
		return errors.Wrap(err, errStr)
	}
	logger.Log.Info("physical apply success: ", outStr)
	return nil
}

func (p *PhysicalLoader) load() error {
	binPath := filepath.Join(p.dbbackupHome, p.innodbCmd.innobackupexBin)

	args := []string{
		fmt.Sprintf("--defaults-file=%s", p.cnf.PhysicalLoad.DefaultsFile),
		fmt.Sprintf(
			"--ibbackup=%s", filepath.Join(p.dbbackupHome, p.innodbCmd.xtrabackupBin)),
	}

	if p.cnf.PhysicalLoad.CopyBack {
		args = append(args, "--copy-back")
	} else {
		args = append(args, "--move-back")
	}

	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		args = append(args, p.cnf.PhysicalLoad.MysqlLoadDir)
	} else {
		args = append(args, []string{
			fmt.Sprintf("--target-dir=%s", p.cnf.PhysicalLoad.MysqlLoadDir),
		}...)
	}

	if strings.Compare(p.mysqlVersion, "008000000") >= 0 && p.isOfficial {
		args = append(args, "--skip-strict")
	}

	// ToDo extraopt
	// xtrabackup 日志输出到当前目录的 logs/xtrabackup_xx.log
	pwd, _ := os.Getwd()
	logfile := filepath.Join(pwd, "logs", fmt.Sprintf("xtrabackup_%d.log", int(time.Now().Weekday())))
	_ = os.MkdirAll(filepath.Dir(logfile), 0755)

	args = append(args, ">>", logfile, "2>&1")
	logger.Log.Info("xtrabackup recover command:", binPath, strings.Join(args, " "))
	outStr, errStr, err := cmutil.ExecCommand(true, "", binPath, args...)
	if err != nil {
		logger.Log.Error("xtrabackup recover failed: ", err, errStr)
		return errors.Wrap(err, errStr)
	}
	logger.Log.Info("xtrabackup recover success: ", outStr)
	return nil
}
