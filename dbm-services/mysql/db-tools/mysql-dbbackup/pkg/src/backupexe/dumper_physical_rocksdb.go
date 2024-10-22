package backupexe

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/pkg/errors"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// PhysicalRocksdbDumper physical rocksdb dumper
type PhysicalRocksdbDumper struct {
	cfg             *config.BackupConfig
	backupLogfile   string
	dbbackupHome    string
	checkpointDir   string
	mysqlVersion    string
	isOfficial      bool
	rocksdbCmd      string
	storageEngine   string
	mysqlRole       string
	masterHost      string
	masterPort      int
	backupStartTime time.Time
	backupEndTime   time.Time
}

// buildArgs construct the instruction parameters for data recovery.
func (p *PhysicalRocksdbDumper) buildArgs() []string {

	targetPath := filepath.Join(p.cfg.Public.BackupDir, p.cfg.Public.TargetName())

	args := []string{
		fmt.Sprintf("--user=%s", p.cfg.Public.MysqlUser),
		fmt.Sprintf("--password=%s", p.cfg.Public.MysqlPasswd),
		fmt.Sprintf("--host=%s", p.cfg.Public.MysqlHost),
		fmt.Sprintf("--port=%d", p.cfg.Public.MysqlPort),
		fmt.Sprintf("--checkpoint_dir=%s", p.checkpointDir),
		fmt.Sprintf("--backup_dir=%s", targetPath),
		"--stream=disabled",
	}

	if strings.ToLower(p.cfg.Public.MysqlRole) == cst.RoleSlave {
		args = append(args, "--slave_info")
	}

	if strings.ToLower(p.cfg.Public.MysqlRole) == cst.RoleMaster {
		args = append(args, "--master_info")
	}

	return args
}

// initConfig init config
func (p *PhysicalRocksdbDumper) initConfig(mysqlVersion string) error {
	if p.cfg == nil {
		return errors.New("rocksdb physical dumper config missed")
	}

	cmdPath, err := os.Executable()

	if err != nil {
		return err
	}

	p.dbbackupHome = filepath.Dir(cmdPath)

	// connect to the mysql and obtain the base information
	db, err := mysqlconn.InitConn(&p.cfg.Public)
	if err != nil {
		logger.Log.Errorf("can not connect to the mysql, host:%s, port:%d, errmsg:%s",
			p.cfg.Public.MysqlHost, p.cfg.Public.MysqlPort, err)
		return err
	}

	defer func() {
		_ = db.Close()
	}()

	p.mysqlVersion, p.isOfficial = util.VersionParser(mysqlVersion)
	p.storageEngine, err = mysqlconn.GetStorageEngine(db)

	if err != nil {
		logger.Log.Errorf("can not get the storage engine from the mysql, host:%s, port:%d, errmsg:%s",
			p.cfg.Public.MysqlHost, p.cfg.Public.MysqlPort, err)
		return err
	}

	// keep the storage engine name is lower
	p.storageEngine = strings.ToLower(p.storageEngine)
	p.mysqlRole = strings.ToLower(p.cfg.Public.MysqlRole)

	// if the current node is slave, obtain the master ip and port
	if p.mysqlRole == cst.RoleSlave || p.mysqlRole == cst.RoleRepeater {
		p.masterHost, p.masterPort, err = mysqlconn.ShowMysqlSlaveStatus(db)
		if err != nil {
			logger.Log.Errorf("can not get the master host and port from the mysql, host:%s, port:%d, errmsg:%s",
				p.cfg.Public.MysqlHost, p.cfg.Public.MysqlPort, err)
			return err
		}
	}

	// set the base config
	p.checkpointDir = filepath.Join(p.cfg.Public.BackupDir, "MyRocks_checkpoint")
	p.rocksdbCmd = filepath.Join("bin", cst.ToolMyrocksHotbackup)
	BackupTool = cst.ToolMyrocksHotbackup
	return nil
}

// Execute Perform data recovery operations.
func (p *PhysicalRocksdbDumper) Execute(enableTimeOut bool) error {
	p.backupStartTime = time.Now()
	defer func() {
		p.backupEndTime = time.Now()
	}()

	// the storage engine must be rocksdb
	if p.storageEngine != cst.StorageEngineRocksdb {
		err := fmt.Errorf("unsupported engine:%s, host:%s, port:%d", p.storageEngine,
			p.cfg.Public.MysqlHost, p.cfg.Public.MysqlPort)
		logger.Log.Error(err)
		return err
	}

	// pre-created checkpoint dir
	_, err := os.Stat(p.checkpointDir)
	if os.IsNotExist(err) {
		logger.Log.Infof("the checkpoint does not exist, will create it. checkpoint:%s", p.checkpointDir)
		err = os.MkdirAll(p.checkpointDir, 0755)
	}

	if err != nil {
		logger.Log.Errorf("can not create the checkpoint:%s, errmsg:%s", p.checkpointDir, err)
		return err
	}

	binPath := filepath.Join(p.dbbackupHome, p.rocksdbCmd)
	args := p.buildArgs()

	// perform the dump operation
	var cmd *exec.Cmd
	backupCmd := fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " "))

	if enableTimeOut {
		timeDiffUinx, err := GetMaxRunningTime(p.cfg.Public.BackupTimeOut)
		if err != nil {
			return err
		}

		ctx, cancel := context.WithTimeout(context.Background(), (time.Duration(timeDiffUinx))*time.Second)
		defer cancel()

		cmd = exec.CommandContext(ctx, "sh", "-c", backupCmd)
	} else {
		cmd = exec.Command("sh", "-c", backupCmd)
	}

	// create a dumper log file to store the log of the dumper command
	p.backupLogfile = fmt.Sprintf("dumper_%s_%s_%d_%d.log", p.storageEngine,
		cst.ToolMyrocksHotbackup, p.cfg.Public.MysqlPort, int(time.Now().Weekday()))

	p.backupLogfile = filepath.Join(p.dbbackupHome, "logs", p.backupLogfile)

	// pre-created dump log file
	outFile, err := os.Create(p.backupLogfile)

	if err != nil {
		logger.Log.Errorf("can not create the dumper log file, file name:%s, errmsg:%s", p.backupLogfile, err)
		return err
	}

	defer func() {
		_ = outFile.Close()
	}()

	// redirect standard output and error messages to a file
	cmd.Stdout = outFile
	cmd.Stderr = outFile

	// perform the dump command
	err = cmd.Run()
	if err != nil {
		logger.Log.Errorf("can not run the rocksdb physical dumper command:%s, engine:%s, errmsg:%s",
			backupCmd, p.storageEngine, err)
		return err
	}

	logger.Log.Infof("dump rocksdb success, command:%s", cmd.String())
	return nil
}

// PrepareBackupMetaInfo generate the metadata of database backup
func (p *PhysicalRocksdbDumper) PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error) {

	// parse the binglog position
	xtrabackupBinlogInfoFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), "xtrabackup_binlog_info")
	xtrabackupSlaveInfoFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), "xtrabackup_slave_info")

	tmpFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), "tmp_dbbackup_go.txt")

	// obtain the qpress command path
	exepath, err := os.Executable()
	if err != nil {
		return nil, err
	}

	exepath = filepath.Dir(exepath)
	qpressPath := filepath.Join(exepath, "bin", "qpress")

	var metaInfo = dbareport.IndexContent{
		BinlogInfo: dbareport.BinlogStatusInfo{},
	}

	// parse the binlog
	masterStatus, err := parseXtraBinlogInfo(qpressPath, xtrabackupBinlogInfoFileName, tmpFileName)
	if err != nil {
		logger.Log.Errorf("do not parse xtrabackup binlog file, file name:%s, errmsg:%s",
			xtrabackupBinlogInfoFileName, err)
		return nil, err
	}

	// save the master node status
	metaInfo.BinlogInfo.ShowMasterStatus = masterStatus
	metaInfo.BinlogInfo.ShowMasterStatus.MasterHost = cnf.Public.MysqlHost
	metaInfo.BinlogInfo.ShowMasterStatus.MasterPort = cnf.Public.MysqlPort

	// parse the information of the master node
	if p.mysqlRole == cst.RoleSlave || p.mysqlRole == cst.RoleRepeater {
		slaveStatus, err := parseXtraSlaveInfo(qpressPath, xtrabackupSlaveInfoFileName, tmpFileName)

		if err != nil {
			logger.Log.Errorf("do not parse xtrabackup slave information, xtrabackup file:%s, errmsg:%s",
				xtrabackupSlaveInfoFileName, err)
			return nil, err
		}

		metaInfo.BinlogInfo.ShowSlaveStatus = slaveStatus
		metaInfo.BinlogInfo.ShowSlaveStatus.MasterHost = p.masterHost
		metaInfo.BinlogInfo.ShowSlaveStatus.MasterPort = p.masterPort
	}

	// teh mark indicating whether the update is a full backup or not
	metaInfo.JudgeIsFullBackup(&cnf.Public)
	if err = os.Remove(tmpFileName); err != nil {
		logger.Log.Errorf("do not delete the tmp file, file name:%s, errmsg:%s", tmpFileName, err)
		return &metaInfo, err
	}

	return &metaInfo, nil
}
