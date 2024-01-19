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
		args = append(args,
			fmt.Sprintf("--target-dir=%s", targetPath),
			"--backup", "--binlog-info=ON", "--lock-ddl",
		)
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

// PrepareBackupMetaInfo prepare the backup result of Physical Backup(innodb)
// xtrabackup备份完成后，解析 xtrabackup_info 等文件
func (p *PhysicalDumper) PrepareBackupMetaInfo(cnf *config.BackupConfig) (*dbareport.IndexContent, error) {
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
	if strings.ToLower(storageEngine) != "innodb" {
		logger.Log.Error(fmt.Sprintf("This is a unknown StorageEngine: %s", storageEngine))
		err := fmt.Errorf("unknown StorageEngine: %s", storageEngine)
		return nil, err
	}

	xtrabackupInfoFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(),
		"xtrabackup_info")
	xtrabackupTimestampFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(),
		"xtrabackup_timestamp_info")
	xtrabackupBinlogInfoFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(),
		"xtrabackup_binlog_info")
	xtrabackupSlaveInfoFileName := filepath.Join(cnf.Public.BackupDir, cnf.Public.TargetName(),
		"xtrabackup_slave_info")

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
	// parse xtrabackup_info
	if err = parseXtraInfo(qpressPath, xtrabackupInfoFileName, tmpFileName, &metaInfo); err != nil {
		return nil, err
	}
	// parse xtrabackup_timestamp_info
	if err := parseXtraTimestamp(qpressPath, xtrabackupTimestampFileName, tmpFileName, &metaInfo); err != nil {
		return nil, err
	}
	// parse xtrabackup_binlog_info
	if masterStatus, err := parseXtraBinlogInfo(qpressPath, xtrabackupBinlogInfoFileName, tmpFileName); err != nil {
		return nil, err
	} else {
		metaInfo.BinlogInfo.ShowMasterStatus = masterStatus
		metaInfo.BinlogInfo.ShowMasterStatus.MasterHost = cnf.Public.MysqlHost
		metaInfo.BinlogInfo.ShowMasterStatus.MasterPort = cnf.Public.MysqlPort
	}

	// parse xtrabackup_slave_info
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
	if err = os.Remove(tmpFileName); err != nil {
		return &metaInfo, err
	}
	return &metaInfo, nil
}
