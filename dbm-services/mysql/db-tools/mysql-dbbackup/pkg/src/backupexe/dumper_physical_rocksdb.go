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

type PhysicalRocksdbDumper struct {
	cfg             *config.BackupConfig
	dbbackupHome    string
	checkpointDir   string
	mysqlVersion    string
	isOfficial      bool
	rocksdbCmd      string
	storageEngine   string
	backupStartTime time.Time
	backupEndTime   time.Time
}

func (p *PhysicalRocksdbDumper) buildArgs() []string {

	targetPath := filepath.Join(p.cfg.Public.BackupDir, p.cfg.Public.TargetName())

	args := []string{
		fmt.Sprintf("--host=%s", p.cfg.Public.MysqlHost),
		fmt.Sprintf("--port=%d", p.cfg.Public.MysqlPort),
		fmt.Sprintf("--user=%s", p.cfg.Public.MysqlUser),
		fmt.Sprintf("--password=%s", p.cfg.Public.MysqlPasswd),
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

func (p *PhysicalRocksdbDumper) initConfig(mysqlVersion string) error {
	if p.cfg == nil {
		return errors.New("rocksdb physical dumper config missed")
	}

	cmdPath, err := os.Executable()

	if err != nil {
		return err
	}

	p.dbbackupHome = filepath.Dir(cmdPath)
	db, err := mysqlconn.InitConn(&p.cfg.Public)

	if err != nil {
		return err
	}

	p.mysqlVersion, p.isOfficial = util.VersionParser(mysqlVersion)
	p.storageEngine, err = mysqlconn.GetStorageEngine(db)

	if err != nil {
		return err
	}
	p.storageEngine = strings.ToLower(p.storageEngine)

	defer func() {
		_ = db.Close()
	}()

	p.checkpointDir = fmt.Sprintf("%s/MyRocks_checkpoint", p.cfg.Public.BackupDir)
	p.rocksdbCmd = "/bin/" + cst.ToolMyrocksHotbackup
	BackupTool = cst.ToolMyrocksHotbackup
	return nil
}

func (p *PhysicalRocksdbDumper) Execute(enableTimeOut bool) error {
	p.backupStartTime = time.Now()
	defer func() {
		p.backupEndTime = time.Now()
	}()

	if p.storageEngine != cst.StorageEnginRocksdb {
		err := fmt.Errorf("%s engine not support", p.storageEngine)
		logger.Log.Error(err)
		return err
	}

	_, err := os.Stat(p.checkpointDir)
	if os.IsNotExist(err) {
		err = os.MkdirAll(p.checkpointDir, 0755)
	}

	if err != nil {
		logger.Log.Errorf("failed to create checkpoint(%s), err-msg:%s", p.checkpointDir, err)
		return err
	}

	binPath := filepath.Join(p.dbbackupHome, p.rocksdbCmd)
	args := p.buildArgs()

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

	backuplogFilename := fmt.Sprintf("%s_backup_%d_%d.log", p.storageEngine, p.cfg.Public.MysqlPort, int(time.Now().Weekday()))
	rocksdbBackuplogFilename := filepath.Join(p.dbbackupHome, "logs", backuplogFilename)

	outFile, err := os.Create(rocksdbBackuplogFilename)

	if err != nil {
		logger.Log.Error("create log file failed: ", err)
		return err
	}

	defer func() {
		_ = outFile.Close()
	}()

	cmd.Stdout = outFile
	cmd.Stderr = outFile
	logger.Log.Info("rocksdb backup command: ", cmd.String())

	err = cmd.Run()
	if err != nil {
		logger.Log.Error("run rocksdb physical backup failed: ", err)
		return err
	}

	return nil
}

func (p *PhysicalRocksdbDumper) PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error) {
	db, err := mysqlconn.InitConn(&cnf.Public)
	if err != nil {
		return nil, errors.WithMessage(err, "IndexContent")
	}

	defer func() {
		_ = db.Close()
	}()

	storageEngine, err := mysqlconn.GetStorageEngine(db)
	if err != nil {
		return nil, err
	}

	storageEngine = strings.ToLower(storageEngine)

	if storageEngine != "rocksdb" {
		logger.Log.Errorf("unknown storage engine(%s)", storageEngine)
		return nil, nil
	}

	xtrabackupBinlogInfoFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), "xtrabackup_binlog_info")
	xtrabackupSlaveInfoFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), "xtrabackup_slave_info")

	tmpFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(), "tmp_dbbackup_go.txt")

	exepath, err := os.Executable()
	if err != nil {
		return nil, err
	}

	exepath = filepath.Dir(exepath)
	qpressPath := filepath.Join(exepath, "bin", "qpress")

	var metaInfo = dbareport.IndexContent{
		BinlogInfo: dbareport.BinlogStatusInfo{},
	}

	if masterStatus, err := parseXtraBinlogInfo(qpressPath, xtrabackupBinlogInfoFileName, tmpFileName); err != nil {
		return nil, err
	} else {
		metaInfo.BinlogInfo.ShowMasterStatus = masterStatus
		metaInfo.BinlogInfo.ShowMasterStatus.MasterHost = cnf.Public.MysqlHost
		metaInfo.BinlogInfo.ShowMasterStatus.MasterPort = cnf.Public.MysqlPort
	}

	if mysqlRole := strings.ToLower(cnf.Public.MysqlRole); mysqlRole == cst.RoleSlave || mysqlRole == cst.RoleRepeater {
		if slaveStatus, err := parseXtraSlaveInfo(qpressPath, xtrabackupSlaveInfoFileName, tmpFileName); err != nil {
			return nil, err
		} else {
			metaInfo.BinlogInfo.ShowSlaveStatus = slaveStatus
			masterHost, masterPort, err := mysqlconn.ShowMysqlSlaveStatus(db)
			if err != nil {
				return nil, err
			}
			metaInfo.BinlogInfo.ShowSlaveStatus.MasterHost = masterHost
			metaInfo.BinlogInfo.ShowSlaveStatus.MasterPort = masterPort
		}
	}

	metaInfo.JudgeIsFullBackup(&cnf.Public)
	if err = os.Remove(tmpFileName); err != nil {
		return &metaInfo, err
	}

	return &metaInfo, nil
}
