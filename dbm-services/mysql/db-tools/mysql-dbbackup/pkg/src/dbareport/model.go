package dbareport

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

type ModelBackupReport struct {
	BackupId        string `json:"backup_id" db:"backup_id"`
	BackupType      string `json:"backup_type" db:"backup_type"`
	ClusterId       int    `json:"cluster_id" db:"cluster_id"`
	ClusterAddress  string `json:"cluster_address" db:"cluster_address"`
	BackupHost      string `json:"backup_host" db:"backup_host"`
	BackupPort      int    `json:"backup_port" db:"backup_port"`
	MysqlRole       string `json:"mysql_role" db:"mysql_role"`
	ShardValue      int    `json:"shard_value" db:"shard_value"`
	BillId          string `json:"bill_id" db:"bill_id"`
	MysqlVersion    string `json:"mysql_version" db:"mysql_version"`
	DataSchemaGrant string `json:"data_schema_grant" db:"data_schema_grant"`
	// IsFullBackup 是否包含数据的全备
	IsFullBackup bool `json:"is_full_backup" db:"is_full_backup"`

	ConsistentBackupTime time.Time `json:"consistent_backup_time" db:"backup_consistent_time"`
	BackupBeginTime      time.Time `json:"backup_begin_time" db:"backup_begin_time"`
	BackupEndTime        time.Time `json:"backup_end_time" db:"backup_end_time"`
	// BinlogInfo show slave status / show master status
	BinlogInfo BinlogStatusInfo `json:"binlog_info" db:"binlog_info"`
	// FileList backup tar file list
	FileList         []IndexFileItem `json:"file_list" db:"file_list"`
	ExtraFields      ExtraFields     `json:"extra_fields" db:"extra_fields"`
	BackupConfigFile string          `json:"backup_config_file" db:"backup_config_file"`
	BackupStatus     string          `json:"backup_status" db:"backup_status"`
}

func (m ModelBackupReport) TableName() string {
	return fmt.Sprintf("%s.%s", cst.INFODBA_SCHEMA, "local_backup_report")
}

// migrateLocalBackupSchema 创建 local_backup_report 表
// 如果 errs 能够处理，自动修复表结构.
func migrateLocalBackupSchema(errs error, db *sql.Conn) error {
	if errs != nil {
		mysqlErr := cmutil.NewMySQLError(errs)
		if !(mysqlErr.Code == 1054 || mysqlErr.Code == 1146) {
			return errors.WithMessage(errs, "error unhandled")
		}
	}
	createTable := fmt.Sprintf(`
CREATE TABLE IF NOT EXISTS %s (
	backup_id varchar(64) NOT NULL,
	mysql_role varchar(30) NOT NULL DEFAULT '',
	shard_value int(11) NOT NULL DEFAULT 0,
	backup_type varchar(30) NOT NULL,
	cluster_id int(11) NOT NULL,
	cluster_address varchar(255) DEFAULT NULL,
	backup_host varchar(30) NOT NULL,
	backup_port int(11) NOT NULL,
	server_id varchar(10) DEFAULT NULL,
	bill_id varchar(30) DEFAULT NULL,
	bk_biz_id int(11) DEFAULT NULL,
	mysql_version varchar(60) DEFAULT NULL,
	data_schema_grant varchar(30) DEFAULT NULL,
	is_full_backup tinyint(4) DEFAULT NULL,
	backup_begin_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
	backup_end_time timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
	backup_consistent_time timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
	backup_status varchar(60) DEFAULT NULL,
	backup_meta_file varchar(255),
	binlog_info text,
	file_list text,
	extra_fields text,
	backup_config_file text,
	PRIMARY KEY (backup_id,mysql_role,shard_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
`, ModelBackupReport{}.TableName())

	var sqlList []string
	dropTable := fmt.Sprintf(`DROP TABLE IF EXISTS %s;`, ModelBackupReport{}.TableName())
	sqlList = append(sqlList, dropTable, createTable)
	logger.Log.Infof("init local_backup_report: %v", sqlList)
	for _, sqlStr := range sqlList {
		if _, err := db.ExecContext(context.Background(), sqlStr); err != nil {
			return errors.WithMessage(err, "create local_backup_report failed")
		}
	}
	logger.Log.Info("migrate table success: local_backup_report")
	return nil
}
