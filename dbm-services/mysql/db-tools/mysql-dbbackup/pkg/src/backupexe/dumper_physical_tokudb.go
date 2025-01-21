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

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// PhysicalTokudbDumper physical tokudb dumper
type PhysicalTokudbDumper struct {
	cfg              *config.BackupConfig
	backupLogfile    string
	dbbackupHome     string
	flushWaitTimeout int
	mysqlVersion     string
	isOfficial       bool
	tokudbCmd        string
	storageEngine    string
	mysqlRole        string
	masterHost       string
	masterPort       int
	backupStartTime  time.Time
	backupEndTime    time.Time
	backupTargetPath string
}

// buildArgs construct the instruction parameters for data recovery.
func (p *PhysicalTokudbDumper) buildArgs() []string {
	// p.backupTargetPath is initialized in initConfig
	args := []string{
		fmt.Sprintf("-u%s", p.cfg.Public.MysqlUser),
		fmt.Sprintf("-p%s", p.cfg.Public.MysqlPasswd),
		fmt.Sprintf("-h%s", p.cfg.Public.MysqlHost),
		fmt.Sprintf("-P%d", p.cfg.Public.MysqlPort),
		fmt.Sprintf("--flush-wait-timeout=%d", p.flushWaitTimeout),
	}
	if strings.ToLower(p.cfg.Public.MysqlRole) == cst.RoleSlave {
		args = append(args, "--dump-slave")
	}
	args = append(args, fmt.Sprintf("%s", p.backupTargetPath))
	return args
}

// initConfig init config
func (p *PhysicalTokudbDumper) initConfig(mysqlVersion string) error {
	if p.cfg == nil {
		return errors.New("tokudb physical dumper config missed")
	}
	if p.flushWaitTimeout == 0 {
		p.flushWaitTimeout = 30
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

	p.backupTargetPath = filepath.Join(p.cfg.Public.BackupDir, p.cfg.Public.TargetName())
	p.tokudbCmd = filepath.Join("bin", cst.ToolTokudbBackup)
	BackupTool = cst.ToolTokudbBackup
	return nil
}

// Execute Perform data recovery operations.
func (p *PhysicalTokudbDumper) Execute(ctx context.Context) error {
	p.backupStartTime = cmutil.TimeToSecondPrecision(time.Now())
	defer func() {
		p.backupEndTime = cmutil.TimeToSecondPrecision(time.Now())
	}()

	// the storage engine must be tokudb
	if p.storageEngine != cst.StorageEngineTokudb {
		err := fmt.Errorf("unsupported engine:%s, host:%s, port:%d", p.storageEngine,
			p.cfg.Public.MysqlHost, p.cfg.Public.MysqlPort)
		logger.Log.Error(err)
		return err
	}

	binPath := filepath.Join(p.dbbackupHome, p.tokudbCmd)
	args := p.buildArgs()

	// perform the dump operation
	var cmd *exec.Cmd
	backupCmd := fmt.Sprintf(`%s %s`, binPath, strings.Join(args, " "))
	cmd = exec.CommandContext(ctx, "sh", "-c", backupCmd)

	// create a dumper log file to store the log of the dumper command
	p.backupLogfile = fmt.Sprintf("dumper_%s_%d_%d.log",
		p.storageEngine, p.cfg.Public.MysqlPort, int(time.Now().Weekday()))
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
	p.backupStartTime = time.Now()
	defer func() {
		p.backupEndTime = time.Now()
	}()
	err = cmd.Run()
	if err != nil {
		logger.Log.Errorf("can not run the tokudb physical dumper command:%s, engine:%s, errmsg:%s",
			backupCmd, p.storageEngine, err)
		return err
	}

	logger.Log.Infof("dump tokudb success, command:%s", cmd.String())
	return nil
}

// PrepareBackupMetaInfo generate the metadata of database backup
func (p *PhysicalTokudbDumper) PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error) {

	// parse the binlog position
	binlogInfoFileName := filepath.Join(p.backupTargetPath, "xtrabackup_binlog_info")
	slaveInfoFileName := filepath.Join(p.backupTargetPath, "xtrabackup_slave_info")
	tmpFileName := filepath.Join(p.backupTargetPath, "tmp_dbbackup_go.txt")

	// obtain the qpress command path
	exepath, err := os.Executable()
	if err != nil {
		return nil, err
	}
	exepath = filepath.Dir(exepath)

	var metaInfo = dbareport.IndexContent{
		BinlogInfo: dbareport.BinlogStatusInfo{},
	}

	// parse the binlog
	masterStatus, err := parseXtraBinlogInfo("", binlogInfoFileName, tmpFileName)
	if err != nil {
		logger.Log.Errorf("do not parse xtrabackup binlog file, file name:%s, errmsg:%s",
			slaveInfoFileName, err)
		return nil, err
	}

	// save the master node status
	metaInfo.BinlogInfo.ShowMasterStatus = masterStatus
	metaInfo.BinlogInfo.ShowMasterStatus.MasterHost = cnf.Public.MysqlHost
	metaInfo.BinlogInfo.ShowMasterStatus.MasterPort = cnf.Public.MysqlPort

	// parse the information of the master node
	if p.mysqlRole == cst.RoleSlave || p.mysqlRole == cst.RoleRepeater {
		slaveStatus, err := parseXtraSlaveInfo("", slaveInfoFileName, tmpFileName)

		if err != nil {
			logger.Log.Errorf("do not parse xtrabackup slave information, xtrabackup file:%s, errmsg:%s",
				slaveInfoFileName, err)
			return nil, err
		}

		metaInfo.BinlogInfo.ShowSlaveStatus = slaveStatus
		metaInfo.BinlogInfo.ShowSlaveStatus.MasterHost = p.masterHost
		metaInfo.BinlogInfo.ShowSlaveStatus.MasterPort = p.masterPort
	}

	// parse xtrabackup_info
	if fileTokudbBegin, err := os.ReadFile(filepath.Join(p.backupTargetPath, "TOKUDB.BEGIN")); err == nil {
		metaInfo.BackupBeginTime, _ = time.ParseInLocation("20060102_150405",
			strings.TrimSpace(string(fileTokudbBegin)), time.Local)
	} else {
		metaInfo.BackupBeginTime = p.backupStartTime
	}
	if fileTokudbEnd, err := os.ReadFile(filepath.Join(p.backupTargetPath, "TOKUDB.END")); err == nil {
		metaInfo.BackupEndTime, _ = time.ParseInLocation("20060102_150405",
			strings.TrimSpace(string(fileTokudbEnd)), time.Local)
	} else {
		metaInfo.BackupEndTime = p.backupEndTime
	}
	metaInfo.BackupConsistentTime = metaInfo.BackupEndTime

	// teh mark indicating whether the update is a full backup or not
	metaInfo.JudgeIsFullBackup(&cnf.Public)
	if err = os.Remove(tmpFileName); err != nil {
		logger.Log.Errorf("do not delete the tmp file, file name:%s, errmsg:%s", tmpFileName, err)
		return &metaInfo, err
	}

	return &metaInfo, nil
}
