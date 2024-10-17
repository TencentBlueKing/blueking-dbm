package backupexe

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"

	"github.com/pkg/errors"
)

type PhysicalRocksdbLoader struct {
	cfg                   *config.BackupConfig
	indexContent          *dbareport.IndexContent
	loaderLogfile         string
	targetName            string
	dataDir               string
	rocksdbDataDir        string
	innodbDataHomeDir     string
	innodbLogGroupHomeDir string
	logbinDir             string
	relaylogDir           string
	tmpDir                string
	slowQueryLogFile      string
	dbbackupHome          string
	checkpointDir         string
	storageEngine         string
	rocksdbCmd            string
}

func (p *PhysicalRocksdbLoader) buildArgs() []string {

	indexFileName := filepath.Base(p.cfg.PhysicalLoad.IndexFilePath)
	result, _ := strings.CutSuffix(indexFileName, ".index")
	p.targetName = filepath.Join(p.cfg.PhysicalLoad.MysqlLoadDir, result)
	p.rocksdbDataDir = filepath.Join(p.dataDir, ".rocksdb")

	args := []string{
		"--move_back",
		fmt.Sprintf("--datadir=%s", p.dataDir),
		fmt.Sprintf("--rocksdb_datadir=%s", p.rocksdbDataDir),
		fmt.Sprintf("--rocksdb_waldir=%s", p.rocksdbDataDir),
		fmt.Sprintf("--backup_dir=%s", p.targetName),
		fmt.Sprintf("--defaults_file=%s", p.cfg.PhysicalLoad.DefaultsFile),
	}

	return args
}

func (p *PhysicalRocksdbLoader) decompress() error {

	err := os.Chdir(p.cfg.Public.BackupDir)
	if err != nil {
		logger.Log.Errorf("do not change to the backup dir:%s, errmsg:%s", p.cfg.Public.BackupDir, err)
		return err
	}

	for _, file := range p.indexContent.FileList {

		if !strings.Contains(file.FileName, ".tar.") {
			continue
		}

		binPath := fmt.Sprintf("tar xf %s -C %s", file.FileName, p.cfg.PhysicalLoad.MysqlLoadDir)

		args := []string{" >> ", p.loaderLogfile, " 2>&1"}
		logger.Log.Info("decompress command:", binPath, strings.Join(args, " "))
		outStr, errStr, err := cmutil.ExecCommand(true, "", binPath, args...)
		if err != nil {
			logger.Log.Errorf("do not decompress the file:%s, errmsg:%s %s", file.FileName, err, errStr)
			return errors.Wrap(err, errStr)
		}

		logger.Log.Infof("decompress success, command:%s, file name:%s, load dir:%s %s",
			binPath, file.FileName, p.cfg.PhysicalLoad.MysqlLoadDir, outStr)
	}

	return nil
}

func (p *PhysicalRocksdbLoader) load() error {

	if p.storageEngine != cst.StorageEngineRocksdb {
		err := fmt.Errorf("unsupported engine:%s, host:%s, port:%d",
			p.storageEngine, p.cfg.Public.MysqlHost, p.cfg.Public.MysqlPort)
		return err
	}

	args := p.buildArgs()

	binPath := filepath.Join(p.dbbackupHome, p.rocksdbCmd)
	loaderCmd := fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " "))
	logger.Log.Infof("rocksdb physical loader command:%s", loaderCmd)

	cmd := exec.Command("sh", "-c", loaderCmd)
	outFile, err := os.Create(p.loaderLogfile)
	if err != nil {
		logger.Log.Errorf("can  not create the loader log file:%s, errmsg:%s", p.loaderLogfile, err)
		return err
	}

	defer func() {
		_ = outFile.Close()
	}()

	cmd.Stdout = outFile
	cmd.Stderr = outFile

	err = cmd.Run()
	if err != nil {
		logger.Log.Errorf("can not run the rocksdb physical loader command:%s, engine:%s, errmsg:%s",
			loaderCmd, p.storageEngine, err)
		return err
	}

	logger.Log.Infof("run load rocksdb success, command:%s", cmd.String())

	// convert to root user and group to mysql.mysql, the mysql server was started by user mysql
	cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", p.dataDir)
	cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", p.innodbLogGroupHomeDir)
	cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", p.innodbDataHomeDir)
	cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", p.logbinDir)
	cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", p.relaylogDir)
	cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", p.slowQueryLogFile)
	cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", p.tmpDir)
	cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", p.rocksdbDataDir)

	return nil
}

func (p *PhysicalRocksdbLoader) initConfig(indexContent *dbareport.IndexContent) error {
	if p.cfg == nil {
		return errors.New("rocksdb physical loader config missed")
	}

	// the user mysql and group mysql is required
	_, err := user.Lookup("mysql")
	if err != nil {
		logger.Log.Errorf("can not lookup the user: mysql, errmsg:%s", err)
		return err
	}

	_, err = user.LookupGroup("mysql")
	if err != nil {
		logger.Log.Errorf("can not lookup the group: mysql, errmsg:%s", err)
		return err
	}

	pwd, err := os.Getwd()
	if err != nil {
		return err
	}

	p.storageEngine = strings.ToLower(indexContent.StorageEngine)
	p.indexContent = indexContent

	p.loaderLogfile = filepath.Join(pwd, "logs", fmt.Sprintf("loader_%s_%s_%d_%d.log",
		p.storageEngine, cst.ToolMyrocksHotbackup, p.cfg.Public.MysqlPort, int(time.Now().Weekday())))

	loaderLogDir := filepath.Dir(p.loaderLogfile)
	err = os.MkdirAll(loaderLogDir, 0755)
	if err != nil {
		logger.Log.Errorf("do not create log dir:%s, errmsg:%s", loaderLogDir, err)
		return err
	}

	cmdPath, err := os.Executable()
	if err != nil {
		return err
	}

	if p.cfg.PhysicalLoad.DefaultsFile == "" {
		return fmt.Errorf("physical load defaults file is required, config file:%s", p.cfg.PhysicalLoad.DefaultsFile)
	}

	if !cmutil.FileExists(p.cfg.PhysicalLoad.DefaultsFile) {
		return fmt.Errorf("the default file no exist, config file:%s", p.cfg.PhysicalLoad.DefaultsFile)
	}

	file, err := os.Open(p.cfg.PhysicalLoad.DefaultsFile)
	if err != nil {
		return fmt.Errorf("can not open the default file, config file:%s", p.cfg.PhysicalLoad.DefaultsFile)
	}

	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "datadir=") {
			p.dataDir = strings.TrimPrefix(line, "datadir=")
			continue
		}

		if strings.HasPrefix(line, "innodb_log_group_home_dir=") {
			p.innodbLogGroupHomeDir = strings.TrimPrefix(line, "innodb_log_group_home_dir=")
			continue
		}

		if strings.HasPrefix(line, "innodb_data_home_dir=") {
			p.innodbDataHomeDir = strings.TrimPrefix(line, "innodb_data_home_dir=")
			continue
		}

		if strings.HasPrefix(line, "log_bin=") {
			p.logbinDir = filepath.Dir(strings.TrimPrefix(line, "log_bin="))
			continue
		}

		if strings.HasPrefix(line, "relay-log=") {
			p.relaylogDir = filepath.Dir(strings.TrimPrefix(line, "relay-log="))
			continue
		}

		if strings.HasPrefix(line, "slow_query_log_file=") {
			p.slowQueryLogFile = filepath.Dir(strings.TrimPrefix(line, "slow_query_log_file="))
			continue
		}

		if strings.HasPrefix(line, "tmpdir=") {
			p.tmpDir = strings.TrimPrefix(line, "tmpdir=")
			continue
		}
	}

	p.dbbackupHome = filepath.Dir(cmdPath)
	p.storageEngine = strings.ToLower(indexContent.StorageEngine)
	p.rocksdbCmd = filepath.Join("bin", cst.ToolMyrocksHotbackup)
	BackupTool = cst.ToolMyrocksHotbackup

	return nil
}

func (p *PhysicalRocksdbLoader) cleanDirs() error {

	logger.Log.Infof("delete the data dir:%s", p.dataDir)
	if p.dataDir != "" {
		os.RemoveAll(p.dataDir)
		os.MkdirAll(p.dataDir, 0755)
	}

	logger.Log.Infof("delete the innodb log group home dir:%s", p.innodbLogGroupHomeDir)
	if p.innodbDataHomeDir != "" {
		os.RemoveAll(p.innodbLogGroupHomeDir)
		os.MkdirAll(p.innodbLogGroupHomeDir, 0755)
	}

	logger.Log.Infof("delete the innodb data home dir:%s", p.innodbDataHomeDir)
	if p.innodbDataHomeDir != "" {
		os.RemoveAll(p.innodbDataHomeDir)
		os.MkdirAll(p.innodbDataHomeDir, 0755)
	}

	logger.Log.Infof("delete the relay log dir:%s", p.relaylogDir)
	if p.relaylogDir != "" {
		os.RemoveAll(p.relaylogDir)
		os.MkdirAll(p.relaylogDir, 0755)
	}

	logger.Log.Infof("delete the log bin dir:%s", p.logbinDir)
	if p.logbinDir != "" {
		os.RemoveAll(p.logbinDir)
		os.MkdirAll(p.logbinDir, 0755)
	}

	logger.Log.Infof("delete the slow query log file:%s", p.slowQueryLogFile)
	if p.slowQueryLogFile != "" {
		os.Remove(p.slowQueryLogFile)
		os.MkdirAll(p.slowQueryLogFile, 0755)
	}

	logger.Log.Infof("delete the tmp dir:%s", p.tmpDir)
	if p.tmpDir != "" {
		os.RemoveAll(p.tmpDir)
		os.MkdirAll(p.tmpDir, 0755)
	}
	return nil
}

func (p *PhysicalRocksdbLoader) Execute() error {
	if p.storageEngine != cst.StorageEngineRocksdb {
		err := fmt.Errorf("unsupported engine:%s", p.storageEngine)
		logger.Log.Error(err)
		return err
	}

	err := p.decompress()
	if err != nil {
		return err
	}

	err = p.cleanDirs()
	if err != nil {
		return err
	}

	err = p.load()
	if err != nil {
		return err
	}

	return nil
}
