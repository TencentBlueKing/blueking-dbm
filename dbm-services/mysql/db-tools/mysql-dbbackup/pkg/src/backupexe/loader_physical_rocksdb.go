package backupexe

import (
	"fmt"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"

	"github.com/pkg/errors"
)

// PhysicalRocksdbLoader physical rocksdb loader
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

// buildArgs construct the instruction parameters for data recovery.
func (p *PhysicalRocksdbLoader) buildArgs() []string {

	p.targetName = p.cfg.PhysicalLoad.MysqlLoadDir
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

// load restore mysql data
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

	// delete *.pid, *.err files
	errFiles := filepath.Join(p.targetName, "*.err")
	pidFiles := filepath.Join(p.targetName, "*.pid")

	logger.Log.Infof("delete the errors file:%s", errFiles)
	cmutil.ExecCommand(true, "", "rm", errFiles)
	logger.Log.Infof("delete the pid file:%s", pidFiles)
	cmutil.ExecCommand(true, "", "rm", pidFiles)

	// run command command
	cmd := exec.Command("sh", "-c", loaderCmd)
	outFile, err := os.Create(p.loaderLogfile)
	if err != nil {
		logger.Log.Errorf("can  not create the loader log file:%s, errmsg:%s", p.loaderLogfile, err)
		return err
	}

	defer func() {
		_ = outFile.Close()
	}()

	// redirect standard output and error messages to a file
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

// initConfig init config
func (p *PhysicalRocksdbLoader) initConfig(indexContent *dbareport.IndexContent) error {
	if p.cfg == nil {
		return errors.New("rocksdb physical loader config missed")
	}

	// the user mysql mysql is required
	_, err := user.Lookup("mysql")
	if err != nil {
		logger.Log.Errorf("can not lookup the user: mysql, errmsg:%s", err)
		return err
	}

	// the group mysql mysql is required
	_, err = user.LookupGroup("mysql")
	if err != nil {
		logger.Log.Errorf("can not lookup the group: mysql, errmsg:%s", err)
		return err
	}

	pwd, err := os.Getwd()
	if err != nil {
		return err
	}

	// keep the storage engine name is lower case
	p.storageEngine = strings.ToLower(indexContent.StorageEngine)
	p.indexContent = indexContent

	p.loaderLogfile = filepath.Join(pwd, "logs", fmt.Sprintf("loader_%s_%s_%d_%d.log",
		p.storageEngine, cst.ToolMyrocksHotbackup, p.cfg.Public.MysqlPort, int(time.Now().Weekday())))

	// obtain the directory where the loader log file is located
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

	// DefaultsFile should be the mysql config(eg: /etc/my.cnf)
	if p.cfg.PhysicalLoad.DefaultsFile == "" {
		return fmt.Errorf("physical load defaults file is required, config file:%s", p.cfg.PhysicalLoad.DefaultsFile)
	}

	if !cmutil.FileExists(p.cfg.PhysicalLoad.DefaultsFile) {
		return fmt.Errorf("the default file no exist, config file:%s", p.cfg.PhysicalLoad.DefaultsFile)
	}

	cnfFile := &util.CnfFile{FileName: p.cfg.PhysicalLoad.DefaultsFile}
	if err := cnfFile.Load(); err != nil {
		return errors.WithMessagef(err, "fail to parse %s", p.cfg.PhysicalLoad.DefaultsFile)
	}
	p.dataDir, err = cnfFile.GetMySQLDataDir()
	p.innodbLogGroupHomeDir, err = cnfFile.GetMysqldKeyVaule("innodb_log_group_home_dir")
	p.innodbDataHomeDir, err = cnfFile.GetMysqldKeyVaule("innodb_data_home_dir")
	p.relaylogDir, err = cnfFile.GetRelayLogDir()
	p.logbinDir, _, err = cnfFile.GetBinLogDir()
	p.tmpDir, err = cnfFile.GetMysqldKeyVaule("tmpdir")
	p.slowQueryLogFile, err = cnfFile.GetMysqldKeyVaule("slow_query_log_file")

	// store the base parameters
	p.dbbackupHome = filepath.Dir(cmdPath)
	p.storageEngine = strings.ToLower(indexContent.StorageEngine)
	p.rocksdbCmd = filepath.Join("bin", cst.ToolMyrocksHotbackup)
	BackupTool = cst.ToolMyrocksHotbackup

	return nil
}

// cleanDirs Before the database resotres the data, it cleans up the existing data.
func (p *PhysicalRocksdbLoader) cleanDirs() error {

	logger.Log.Infof("delete the data dir:%s", p.dataDir)
	if p.dataDir != "" && p.dataDir != "/" {
		// delete the old directory
		os.RemoveAll(p.dataDir)
		// create the new directory
		os.MkdirAll(p.dataDir, 0755)
	}

	logger.Log.Infof("delete the innodb log group home dir:%s", p.innodbLogGroupHomeDir)
	if p.innodbLogGroupHomeDir != "" && p.innodbLogGroupHomeDir != "/" {
		// delete the old directory
		os.RemoveAll(p.innodbLogGroupHomeDir)
		// create the new directory
		os.MkdirAll(p.innodbLogGroupHomeDir, 0755)
	}

	logger.Log.Infof("delete the innodb data home dir:%s", p.innodbDataHomeDir)
	if p.innodbDataHomeDir != "" && p.innodbDataHomeDir != "/" {
		// delete the old directory
		os.RemoveAll(p.innodbDataHomeDir)
		// create the new directory
		os.MkdirAll(p.innodbDataHomeDir, 0755)
	}

	logger.Log.Infof("delete the relay log dir:%s", p.relaylogDir)
	if p.relaylogDir != "" && p.relaylogDir != "/" {
		// delete the old directory
		os.RemoveAll(p.relaylogDir)
		// create the new directory
		os.MkdirAll(p.relaylogDir, 0755)
	}

	logger.Log.Infof("delete the log bin dir:%s", p.logbinDir)
	if p.logbinDir != "" && p.logbinDir != "/" {
		// delete the old directory
		os.RemoveAll(p.logbinDir)
		// create the new directory
		os.MkdirAll(p.logbinDir, 0755)
	}

	logger.Log.Infof("delete the slow query log file:%s", p.slowQueryLogFile)
	if p.slowQueryLogFile != "" && p.slowQueryLogFile != "/" {
		// delete the old directory
		os.Remove(p.slowQueryLogFile)
		// create the new directory
		os.MkdirAll(p.slowQueryLogFile, 0755)
	}

	logger.Log.Infof("delete the tmp dir:%s", p.tmpDir)
	if p.tmpDir != "" && p.tmpDir != "/" {
		// delete the old directory
		os.RemoveAll(p.tmpDir)
		// create the new directory
		os.MkdirAll(p.tmpDir, 0755)
	}
	return nil
}

// Execute Perform data recovery operations.
func (p *PhysicalRocksdbLoader) Execute() error {

	// the storage engine must be rocksdb
	if p.storageEngine != cst.StorageEngineRocksdb {
		err := fmt.Errorf("unsupported engine:%s", p.storageEngine)
		logger.Log.Error(err)
		return err
	}

	// delete the old directory used to restore the backup data
	err := p.cleanDirs()
	if err != nil {
		return err
	}

	// restore the backup data
	err = p.load()
	if err != nil {
		return err
	}

	return nil
}
