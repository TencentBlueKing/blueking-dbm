package dbareport

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/mysqlconn"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/parsecnf"

	"github.com/pkg/errors"
	"github.com/spf13/cast"
)

// BackupResult the reported dump file
type BackupResult struct {
	BackupId             string           `json:"backup_id"`
	BillId               string           `json:"bill_id"`
	BkBizId              string           `json:"bk_biz_id"`
	BkCloudId            string           `json:"bk_cloud_id"`
	TimeZone             string           `json:"time_zone"`
	ClusterId            string           `json:"cluster_id"`
	ClusterAddress       string           `json:"cluster_address"`
	ShardValue           int              `ini:"shard_value"` // 分片 id，仅 spider 有用
	MysqlHost            string           `json:"mysql_host"`
	MysqlPort            int              `json:"mysql_port"`
	MasterHost           string           `json:"master_host"`
	MasterPort           int              `json:"master_port"`
	MysqlRole            string           `json:"mysql_role"`
	BinlogInfo           BinlogStatusInfo `json:"binlog_info"`
	FileName             string           `json:"file_name"`
	BackupBeginTime      string           `json:"backup_begin_time"`
	BackupEndTime        string           `json:"backup_end_time"`
	DataSchemaGrant      string           `json:"data_schema_grant"`
	BackupType           string           `json:"backup_type"`
	ConsistentBackupTime string           `json:"consistent_backup_time"`
	FileSize             int64            `json:"file_size"`
	FileType             string           `json:"file_type"`
	TaskId               string           `json:"task_id"`
}

// BinlogStatusInfo master status and slave status
type BinlogStatusInfo struct {
	ShowMasterStatus *StatusInfo `json:"show_master_status"`
	ShowSlaveStatus  *StatusInfo `json:"show_slave_status"`
}

// StatusInfo detailed binlog information
type StatusInfo struct {
	BinlogFile string `json:"binlog_file"`
	BinlogPos  string `json:"binlog_pos"`
	Gtid       string `json:"gtid"`
	MasterHost string `json:"master_host"`
	MasterPort int    `json:"master_port"`
}

// PrepareLogicalBackupInfo prepare the backup result of Logical Backup
func (b *BackupResult) PrepareLogicalBackupInfo(cnf *parsecnf.Cnf) error {
	metaFileName := filepath.Join(cnf.Public.BackupDir, common.TargetName, "metadata")
	metadata, err := parseMydumperMetadata(metaFileName)
	if err != nil {
		return errors.WithMessage(err, "parse mydumper metadata")
	}
	logger.Log.Infof("metadata file:%+v", metadata)
	b.BackupBeginTime = metadata.DumpStarted
	b.ConsistentBackupTime = metadata.DumpStarted
	b.BackupEndTime = metadata.DumpFinished
	b.BinlogInfo.ShowMasterStatus = &StatusInfo{
		BinlogFile: metadata.MasterStatus["File"],
		BinlogPos:  metadata.MasterStatus["Position"],
		Gtid:       metadata.MasterStatus["Executed_Gtid_Set"],
		MasterHost: cnf.Public.MysqlHost, // use backup_host as local binlog file_pos host
		MasterPort: cast.ToInt(cnf.Public.MysqlPort),
	}
	if strings.ToLower(cnf.Public.MysqlRole) == cst.RoleSlave {
		b.BinlogInfo.ShowSlaveStatus = &StatusInfo{
			BinlogFile: metadata.SlaveStatus["Relay_Master_Log_File"],
			BinlogPos:  metadata.SlaveStatus["Exec_Master_Log_Pos"],
			Gtid:       metadata.SlaveStatus["Executed_Gtid_Set"],
			MasterHost: metadata.SlaveStatus["Master_Host"],
			MasterPort: cast.ToInt(metadata.SlaveStatus["Master_Port"]),
		}
	}
	return nil
}

// PrepareXtraBackupInfo prepare the backup result of Physical Backup(innodb)
func (b *BackupResult) PrepareXtraBackupInfo(cnf *parsecnf.Cnf) error {
	xtrabackupInfoFileName := filepath.Join(cnf.Public.BackupDir, common.TargetName, "xtrabackup_info")
	xtrabackupTimestampFileName := filepath.Join(cnf.Public.BackupDir, common.TargetName, "xtrabackup_timestamp_info")
	xtrabackupBinlogInfoFileName := filepath.Join(cnf.Public.BackupDir, common.TargetName, "xtrabackup_binlog_info")
	xtrabackupSlaveInfoFileName := filepath.Join(cnf.Public.BackupDir, common.TargetName, "xtrabackup_slave_info")
	tmpFileName := filepath.Join(cnf.Public.BackupDir, common.TargetName, "tmp_dbbackup_go.txt")
	exepath, err := os.Executable()
	if err != nil {
		return err
	}
	exepath = filepath.Dir(exepath)
	binpath := filepath.Join(exepath, "/bin/xtrabackup", "qpress")

	// parse xtrabackup_info
	if err := parseXtraInfo(b, binpath, xtrabackupInfoFileName, tmpFileName); err != nil {
		return err
	}

	// parse xtrabackup_timestamp_info
	if err := parseXtraTimestamp(b, binpath, xtrabackupTimestampFileName, tmpFileName); err != nil {
		return err
	}

	// parse xtrabackup_binlog_info
	if err := parseXtraBinlogInfo(b, binpath, xtrabackupBinlogInfoFileName, tmpFileName); err != nil {
		return err
	}

	// parse xtrabackup_slave_info
	if strings.ToLower(cnf.Public.MysqlRole) == cst.RoleSlave {
		if err := parseXtraSlaveInfo(b, binpath, xtrabackupSlaveInfoFileName, tmpFileName); err != nil {
			return err
		}
	}

	if err = os.Remove(tmpFileName); err != nil {
		return err
	}

	return nil
}

// BuildBaseBackupResult Build based BackupResult
func (b *BackupResult) BuildBaseBackupResult(cnf *parsecnf.Cnf, uuid string) error {
	b.BackupId = uuid
	b.BillId = cnf.Public.BillId
	b.BkBizId = cnf.Public.BkBizId
	b.BkCloudId = cnf.Public.BkCloudId
	b.ClusterAddress = cnf.Public.ClusterAddress
	b.ShardValue = cnf.Public.ShardValue
	b.ClusterId = cnf.Public.ClusterId
	b.MysqlHost = cnf.Public.MysqlHost
	b.MysqlPort = cast.ToInt(cnf.Public.MysqlPort)
	b.DataSchemaGrant = cnf.Public.DataSchemaGrant
	b.MysqlRole = cnf.Public.MysqlRole
	b.BackupType = cnf.Public.BackupType
	b.TimeZone, _ = time.Now().Zone()
	DB, err := mysqlconn.InitConn(&cnf.Public)
	if err != nil {
		return errors.WithMessage(err, "BuildBaseBackupResult")
	}
	defer DB.Close()

	masterHost, masterPort, err := mysqlconn.ShowMysqlSlaveStatus(&cnf.Public)
	if err != nil {
		return err
	}
	b.MasterHost = masterHost
	b.MasterPort = masterPort

	if strings.ToLower(cnf.Public.BackupType) == "logical" {
		if err := b.PrepareLogicalBackupInfo(cnf); err != nil {
			return err
		}
	} else if strings.ToLower(cnf.Public.BackupType) == "physical" {
		storageEngine, err := mysqlconn.GetStorageEngine(DB)
		if err != nil {
			return err
		}
		if strings.ToLower(storageEngine) == "innodb" {
			if err := b.PrepareXtraBackupInfo(cnf); err != nil {
				return err
			}
		} else {
			logger.Log.Error(fmt.Sprintf("This is a unknown StorageEngine: %s", storageEngine))
			err := fmt.Errorf("unknown StorageEngine: %s", storageEngine)
			return err
		}
	}
	return nil
}
