package backupexe

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// PhysicalRocksdbDumper physical rocksdb dumper
type PhysicalRocksdbDumper struct {
	cnf             *config.BackupConfig
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

	targetPath := filepath.Join(p.cnf.Public.BackupDir, p.cnf.Public.TargetName())

	args := []string{
		fmt.Sprintf("--user=%s", p.cnf.Public.MysqlUser),
		fmt.Sprintf("--password=%s", p.cnf.Public.MysqlPasswd),
		fmt.Sprintf("--host=%s", p.cnf.Public.MysqlHost),
		fmt.Sprintf("--port=%d", p.cnf.Public.MysqlPort),
		fmt.Sprintf("--checkpoint_dir=%s", p.checkpointDir),
		fmt.Sprintf("--backup_dir=%s", targetPath),
		"--slave_info",
		"--master_info",
		"--stream=disabled",
	}

	return args
}

// initConfig init config
func (p *PhysicalRocksdbDumper) initConfig(mysqlVersion string, logBinDisabled bool) error {
	if p.cnf == nil {
		return errors.New("rocksdb physical dumper config missed")
	}

	cmdPath, err := os.Executable()

	if err != nil {
		return err
	}

	p.dbbackupHome = filepath.Dir(cmdPath)

	// connect to the mysql and obtain the base information
	db, err := mysqlconn.InitConn(&p.cnf.Public)
	if err != nil {
		logger.Log.Errorf("can not connect to the mysql, host:%s, port:%d, errmsg:%s",
			p.cnf.Public.MysqlHost, p.cnf.Public.MysqlPort, err)
		return err
	}

	defer func() {
		_ = db.Close()
	}()

	p.mysqlVersion, p.isOfficial = util.VersionParser(mysqlVersion)
	p.storageEngine, err = mysqlconn.GetStorageEngine(db)

	if err != nil {
		logger.Log.Errorf("can not get the storage engine from the mysql, host:%s, port:%d, errmsg:%s",
			p.cnf.Public.MysqlHost, p.cnf.Public.MysqlPort, err)
		return err
	}

	// keep the storage engine name is lower
	p.storageEngine = strings.ToLower(p.storageEngine)
	p.mysqlRole = strings.ToLower(p.cnf.Public.MysqlRole)

	// if the current node is slave, obtain the master ip and port
	if p.mysqlRole == cst.RoleSlave || p.mysqlRole == cst.RoleRepeater {
		p.masterHost, p.masterPort, err = mysqlconn.ShowMysqlSlaveStatus(db)
		if err != nil {
			logger.Log.Errorf("can not get the master host and port from the mysql, host:%s, port:%d, errmsg:%s",
				p.cnf.Public.MysqlHost, p.cnf.Public.MysqlPort, err)
			return err
		}
	}

	// set the base config
	p.checkpointDir = filepath.Join(p.cnf.Public.BackupDir, "MyRocks_checkpoint", strconv.Itoa(p.cnf.Public.MysqlPort))
	p.rocksdbCmd = filepath.Join("bin", cst.ToolMyrocksHotbackup)
	BackupTool = cst.ToolMyrocksHotbackup
	return nil
}

// Execute Perform data recovery operations.
func (p *PhysicalRocksdbDumper) Execute(ctx context.Context) error {
	// the storage engine must be rocksdb
	if p.storageEngine != cst.StorageEngineRocksdb {
		err := fmt.Errorf("unsupported engine:%s, host:%s, port:%d", p.storageEngine,
			p.cnf.Public.MysqlHost, p.cnf.Public.MysqlPort)
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
	if p.cnf.BackupToRemote.EnableRemote {
		return errors.Errorf("remote backup not support rocksdb")
	}
	// perform the dump operation
	var cmd *exec.Cmd
	backupCmd := fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " "))
	cmd = exec.CommandContext(ctx, "sh", "-c", backupCmd)

	// create a dumper log file to store the log of the dumper command
	p.backupLogfile = fmt.Sprintf("dumper_%s_%s_%d_%d.log", p.storageEngine,
		cst.ToolMyrocksHotbackup, p.cnf.Public.MysqlPort, int(time.Now().Weekday()))

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
	p.backupStartTime = cmutil.TimeToSecondPrecision(time.Now())
	defer func() {
		p.backupEndTime = cmutil.TimeToSecondPrecision(time.Now())
	}()
	err = cmd.Run()
	if err != nil {
		logger.Log.Errorf("can not run the rocksdb physical dumper command:%s, engine:%s, errmsg:%s",
			mysqlcomm.RemoveMysqlCommandPassword(backupCmd), p.storageEngine, err)
		return err
	}

	logger.Log.Infof("dump rocksdb success, command:%s", cmd.String())
	return nil
}

// PrepareBackupMetaInfo generate the metadata of database backup
func (p *PhysicalRocksdbDumper) PrepareBackupMetaInfo(cnf *config.BackupConfig, metaInfo *dbareport.IndexContent) error {
	metaInfo.BackupMetaFileBase = dbareport.BackupMetaFileBase{
		BackupBeginTime: p.backupStartTime,
		BackupEndTime:   p.backupEndTime,
	}
	backupTargetDir := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName())
	xtrabackupBinlogInfoFileName := filepath.Join(backupTargetDir, "xtrabackup_binlog_info")
	xtrabackupSlaveInfoFileName := filepath.Join(backupTargetDir, "xtrabackup_slave_info")
	xtrabackupTimestampFileName := filepath.Join(backupTargetDir, "xtrabackup_timestamp_info")
	tmpFileName := filepath.Join(backupTargetDir, "tmp_dbbackup_go.txt")

	// obtain the qpress command path
	exepath, err := os.Executable()
	if err != nil {
		return err
	}
	exepath = filepath.Dir(exepath)
	qpressPath := filepath.Join(exepath, "bin", "qpress")

	// parse xtrabackup_timestamp_info
	if err := parseXtraTimestamp(qpressPath, xtrabackupTimestampFileName, tmpFileName, metaInfo); err != nil {
		// 此时刚备份完成，还没有开始打包，这里把当前时间认为是 consistent_time，不完善！
		logger.Log.Warnf("xtrabackup_timestamp_info file not found, "+
			"use current time as Consistent Time, err: %s", err.Error())
		metaInfo.BackupConsistentTime = cmutil.TimeToSecondPrecision(metaInfo.BackupEndTime)
	}
	// parse the binlog
	masterStatus, err := parseXtraBinlogInfo(qpressPath, xtrabackupBinlogInfoFileName, tmpFileName)
	if err != nil {
		logger.Log.Errorf("can not parse xtrabackup_binlog_info, errmsg:%s", err)
	} else {
		logger.Log.Infof("xtrabackup_binlog_info binlog file:%s pos:%s",
			masterStatus.BinlogFile, masterStatus.BinlogPos)
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
			return err
		}
		if metaInfo.BinlogInfo.ShowSlaveStatus == nil {
			metaInfo.BinlogInfo.ShowSlaveStatus = &dbareport.StatusInfo{}
		}
		metaInfo.BinlogInfo.ShowSlaveStatus.BinlogFile = slaveStatus.BinlogFile
		metaInfo.BinlogInfo.ShowSlaveStatus.BinlogPos = slaveStatus.BinlogPos
		if p.masterHost != "" {
			metaInfo.BinlogInfo.ShowSlaveStatus.MasterHost = p.masterHost
		}
		if p.masterPort != 0 {
			metaInfo.BinlogInfo.ShowSlaveStatus.MasterPort = p.masterPort
		}
	}

	// teh mark indicating whether the update is a full backup or not
	metaInfo.JudgeIsFullBackup(&cnf.Public)
	if err = os.Remove(tmpFileName); err != nil {
		logger.Log.Errorf("do not delete the tmp file, file name:%s, errmsg:%s", tmpFileName, err)
		return err
	}

	return nil
}
