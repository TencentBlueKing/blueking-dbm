package backupexe

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/spf13/cast"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/util"
)

// PhysicalDumper TODO
type PhysicalDumper struct {
	cnf                         *config.BackupConfig
	dbbackupHome                string
	mysqlVersion                string // parsed
	isOfficial                  bool
	innodbCmd                   InnodbCommand
	storageEngine               string
	backupStartTime             time.Time
	backupEndTime               time.Time
	tmpDisableSlaveMultiThreads bool
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

	varSlaveParallelWorkers, err := mysqlconn.GetSingleGlobalVar("slave_parallel_workers", db)
	if err != nil && cmutil.NewMySQLError(err).Code == 1193 { // Unknown system variable
		logger.Log.Infof("fail to query slave_parallel_workers, err:%s", err.Error())
	} else if cast.ToInt(varSlaveParallelWorkers) > 0 &&
		p.cnf.PhysicalBackup.DisableSlaveMultiThread &&
		p.cnf.Public.MysqlRole == cst.RoleSlave {
		varGtidMode, err := mysqlconn.GetSingleGlobalVar("gtid_mode", db)
		if err != nil && cmutil.NewMySQLError(err).Code == 1193 { // Unknown system variable
			logger.Log.Warnf("fail to query gtid_mode, err:%s", err.Error())
		} else if !cast.ToBool(varGtidMode) {
			logger.Log.Infof("will set slave_parallel_workers=0 temporary for slave backup")
			p.tmpDisableSlaveMultiThreads = true
		}
	}

	if err := p.innodbCmd.ChooseXtrabackupTool(p.mysqlVersion, p.isOfficial); err != nil {
		return err
	}
	BackupTool = cst.ToolXtrabackup
	return nil
}

// buildArgs 生成 xtrabackup 的命令行参数
func (p *PhysicalDumper) buildArgs() []string {
	args := []string{
		fmt.Sprintf("--defaults-file=%s", p.cnf.PhysicalBackup.DefaultsFile),
		fmt.Sprintf("--host=%s", p.cnf.Public.MysqlHost),
		fmt.Sprintf("--port=%d", p.cnf.Public.MysqlPort),
		fmt.Sprintf("--user=%s", p.cnf.Public.MysqlUser),
		fmt.Sprintf("--password=%s", p.cnf.Public.MysqlPasswd),
		"--compress",
	}

	targetPath := filepath.Join(p.cnf.Public.BackupDir, p.cnf.Public.TargetName())
	if strings.Compare(p.mysqlVersion, "005007000") < 0 {
		args = append(args, targetPath)
	} else {
		args = append(args,
			fmt.Sprintf("--target-dir=%s", targetPath),
			"--backup", "--lock-ddl",
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
			"--slave-info",
			//"--safe-slave-backup",
		}...)
	}

	if strings.Compare(p.mysqlVersion, "008000000") >= 0 {
		if p.isOfficial {
			args = append(args, "--skip-strict")
		}
	} else { // xtrabackup_80 has no this args, and will report errors
		args = append(args, "--no-timestamp", "--lazy-backup-non-innodb", "--wait-last-flush=2")
		args = append(args, fmt.Sprintf("--ibbackup=%s", filepath.Join(p.dbbackupHome, p.innodbCmd.xtrabackupBin)))
		if strings.Compare(p.mysqlVersion, "005007000") > 0 {
			args = append(args, "--binlog-info=ON")
		}
	}

	// ToDo extropt
	return args
}

// Execute excute dumping backup with physical backup tool
func (p *PhysicalDumper) Execute(enableTimeOut bool) error {
	p.backupStartTime = time.Now()
	defer func() {
		p.backupEndTime = time.Now()
	}()
	if p.storageEngine != "innodb" {
		err := fmt.Errorf("%s engine not support", p.storageEngine)
		logger.Log.Error(err.Error())
		return err
	}

	binPath := filepath.Join(p.dbbackupHome, p.innodbCmd.innobackupexBin)
	args := p.buildArgs()

	// DisableSlaveMultiThreads 这个选项要在主函数里设置，备份结束(成功/失败)后 defer 关闭
	if p.tmpDisableSlaveMultiThreads {
		db, err := mysqlconn.InitConn(&p.cnf.Public)
		if err != nil {
			return err
		}
		defer func() {
			_ = db.Close()
		}()
		if originVal, err := mysqlconn.SetGlobalVarAndReturnOrigin("slave_parallel_workers", "0", db); err != nil {
			logger.Log.Errorf("set global slave_parallel_workers=0 failed, err: %s", err.Error())
			return err
		} else {
			logger.Log.Infof("will set global slave_parallel_workers=%s after backup finished", originVal)
			defer func() {
				if err = mysqlconn.SetSingleGlobalVar("slave_parallel_workers", originVal, db); err != nil {
					logger.Log.Errorf("set global slave_parallel_workers=%s failed, err: %s", originVal, err.Error())
				}
			}()
		}
	}

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

	outFile, err := os.Create(filepath.Join(logger.GetLogDir(),
		fmt.Sprintf("xtrabackup_%d_%d.log", p.cnf.Public.MysqlPort, int(time.Now().Weekday()))))
	if err != nil {
		logger.Log.Error("create log file failed: ", err)
		return err
	}
	defer func() {
		_ = outFile.Close()
	}()

	cmd.Stdout = outFile
	//cmd.Stderr = outFile
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	logger.Log.Info("xtrabackup command: ", cmd.String())

	err = cmd.Run()
	if err != nil {
		logger.Log.Error("run physical backup failed: ", err, stderr.Bytes())
		return errors.WithMessage(err, stderr.String())
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
		logger.Log.Warnf("xtrabackup_info file not found, use current time as BackupEndTime, err: %s", err.Error())
		metaInfo.BackupBeginTime, _ = time.Parse(time.DateTime, p.backupStartTime.Format(time.DateTime))
		metaInfo.BackupEndTime, _ = time.Parse(time.DateTime, p.backupEndTime.Format(time.DateTime))
	}
	// parse xtrabackup_timestamp_info
	if err := parseXtraTimestamp(qpressPath, xtrabackupTimestampFileName, tmpFileName, &metaInfo); err != nil {
		// 此时刚备份完成，还没有开始打包，这里把当前时间认为是 consistent_time，不完善！
		logger.Log.Warnf("xtrabackup_timestamp_info file not found, "+
			"use current time as Consistent Time, err: %s", err.Error())
		metaInfo.BackupConsistentTime, _ = time.Parse(time.DateTime, p.backupEndTime.Format(time.DateTime))
	}
	// parse xtrabackup_binlog_info 本机的 binlog file,pos
	if masterStatus, err := parseXtraBinlogInfo(qpressPath, xtrabackupBinlogInfoFileName, tmpFileName); err != nil {
		return nil, err
	} else {
		metaInfo.BinlogInfo.ShowMasterStatus = masterStatus
		metaInfo.BinlogInfo.ShowMasterStatus.MasterHost = cnf.Public.MysqlHost
		metaInfo.BinlogInfo.ShowMasterStatus.MasterPort = cnf.Public.MysqlPort
	}

	// parse xtrabackup_slave_info 如果是 slave，获取它的 master file,pos
	if mysqlRole := strings.ToLower(cnf.Public.MysqlRole); mysqlRole == cst.RoleSlave || mysqlRole == cst.RoleRepeater {
		if slaveStatus, err := parseXtraSlaveInfo(qpressPath, xtrabackupSlaveInfoFileName, tmpFileName); err != nil {
			logger.Log.Warnf("parse xtrabackup_slave_info with error for role=%s %s:%d , err: %s",
				cnf.Public.MysqlRole, cnf.Public.MysqlHost, cnf.Public.MysqlPort, err.Error())
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
