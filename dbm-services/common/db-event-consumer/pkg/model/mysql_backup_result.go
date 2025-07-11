// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import (
	"encoding/json"
	"log/slog"
	"time"

	sq "github.com/Masterminds/squirrel"
	"github.com/jinzhu/copier"
	"github.com/pkg/errors"
	"gorm.io/gorm"

	"dbm-services/common/db-event-consumer/pkg/sinker"
)

type MysqlBackupResultModel struct {
	BaseModel `xorm:"extends"`

	BackupId        string `json:"backup_id" db:"backup_id" gorm:"column:backup_id;type:varchar(32);NOT NULL;index:uk_cluster,unique,priority:4"`
	BackupType      string `json:"backup_type" db:"backup_type" gorm:"column:backup_type;type:varchar(32);NOT NULL"`
	ClusterId       int    `json:"cluster_id" db:"cluster_id" gorm:"column:cluster_id;type:int;NOT NULL"`
	ClusterAddress  string `json:"cluster_address" db:"cluster_address" gorm:"column:cluster_address;type:varchar(32);NOT NULL;index:uk_cluster,unique,priority:1"`
	BackupHost      string `json:"backup_host" db:"backup_host" gorm:"column:backup_host;type:varchar(32);NOT NULL;index:uk_hostport,unique,priority:1"`
	BackupPort      int    `json:"backup_port" db:"backup_port" gorm:"column:backup_port;type:int;NOT NULL;index:uk_hostport,unique,priority:2"`
	MysqlRole       string `json:"mysql_role" db:"mysql_role" gorm:"column:mysql_role;type:varchar(32);NOT NULL;index:uk_hostport,unique,priority:3;;index:uk_cluster,unique,priority:3"`
	ShardValue      int    `json:"shard_value" db:"shard_value" gorm:"column:shard_value;type:int;NOT NULL;index:uk_cluster,unique,priority:2"`
	BillId          string `json:"bill_id" db:"bill_id" gorm:"column:bill_id;type:varchar(32);NOT NULL"`
	BkBizId         int    `json:"bk_biz_id" db:"bk_biz_id" gorm:"column:bk_biz_id;type:int;NOT NULL"`
	MysqlVersion    string `json:"mysql_version" db:"mysql_version" gorm:"column:mysql_version;type:varchar(32);NOT NULL"`
	DataSchemaGrant string `json:"data_schema_grant" db:"data_schema_grant" gorm:"column:data_schema_grant;type:varchar(32);NOT NULL"`
	// IsFullBackup 是否包含数据的全备
	IsFullBackup     bool   `json:"is_full_backup" db:"is_full_backup" gorm:"column:is_full_backup;type:tinyint;NOT NULL"`
	FileRetentionTag string `json:"file_retention_tag" db:"file_retention_tag" gorm:"column:file_retention_tag;type:varchar(32);NOT NULL"`
	TotalFilesize    uint64 `json:"total_filesize" db:"total_filesize" gorm:"column:total_filesize;type:bigint;NOT NULL"`

	BackupConsistentTime time.Time       `json:"backup_consistent_time" db:"backup_consistent_time" gorm:"column:backup_consistent_time;type:datetime;NOT NULL;index:uk_hostport,unique,priority:4"`
	BackupBeginTime      time.Time       `json:"backup_begin_time" db:"backup_begin_time" gorm:"column:backup_begin_time;type:datetime;NOT NULL"`
	BackupEndTime        time.Time       `json:"backup_end_time" db:"backup_end_time" gorm:"column:backup_end_time;type:datetime;NOT NULL"`
	BinlogInfo           json.RawMessage `json:"binlog_info" db:"binlog_info" gorm:"column:binlog_info;type:text;NOT NULL"`
	FileList             json.RawMessage `json:"file_list" db:"file_list" gorm:"column:file_list;type:text;NOT NULL"`
	ExtraFields          json.RawMessage `json:"extra_fields" db:"extra_fields" gorm:"column:extra_fields;type:text;NOT NULL"`
	/*
		// BinlogInfo show slave status / show master status
		BinlogInfo BinlogStatusInfo `json:"binlog_info" db:"binlog_info"`
		// FileList backup tar file list
		FileList     []TarFileItem `json:"file_list" db:"file_list"`
		ExtraFields  ExtraFields   `json:"extra_fields" db:"extra_fields"`
	*/
	BackupStatus string `json:"backup_status" db:"backup_status" gorm:"column:backup_status;type:varchar(32);NOT NULL"`
	// UNIQUE KEY `uk_hostport` (`backup_host`,`backup_port`,`mysql_role`,`backup_consistent_time`)
	// UNIQUE KEY `uk_cluster` (`cluster_address`,`shard_value`,`mysql_role`,`backup_id`),
}

func (m MysqlBackupResultModel) TableName() string {
	return "tb_mysql_backup_result"
}

func (m MysqlBackupResultModel) MigrateSchema(w sinker.DSWriter) error {
	slog.Info("run migrate for MysqlBackupResultModel", slog.String("table", m.TableName()))
	if w.Type() == "mysql" {
		dbWriter := w.(*sinker.MysqlWriter)
		db := dbWriter.GormDB()
		if err := db.Migrator().AutoMigrate(&m); err != nil {
			return err
		}
		/*
			if err := AddIndex(db, m.TableName(), "uk_hostport",
				[]string{"backup_host", "backup_port", "mysql_role", "backup_consistent_time"}, true, true); err != nil {
				return err
			}
			if err := AddIndex(db, m.TableName(), "uk_cluster",
				[]string{"cluster_address", "shard_value", "mysql_role", "backup_id"}, true, true); err != nil {
				return err
			}
		*/
		if err := CreateOrUpdateIndex(db, m.TableName(), "idx_backuptime",
			[]string{"backup_consistent_time"}, false, true); err != nil {
			return err
		}
		if err := CreateOrUpdateIndex(db, m.TableName(), "idx_backupid",
			[]string{"backup_id"}, false, true); err != nil {
			return err
		}
		return nil
	} else if w.Type() == "mysql_xorm" {
		return w.AutoMigrate(m)
	} else {
		return w.AutoMigrate(m)
	}
}

func (m MysqlBackupResultModel) Create(objs interface{}, w sinker.DSWriter) error {
	if w.Type() == "mysql" {
		if writer, ok := w.(*sinker.MysqlWriter); ok {
			return m.mysqlCreate(objs, writer.GormDB())
		} else if writer, ok := w.(*sinker.XormWriter); ok {
			return errors.Errorf("not implement custom writer: %s", writer.Type())
		} else {
			return errors.Errorf("not implement custom writer: %s", w.Type())
		}
	} else {
		newObj := objs.([]MysqlBackupResultModel)
		return w.WriteBatch(m, newObj)
	}
}

func (m MysqlBackupResultModel) mysqlCreate(i interface{}, db *gorm.DB) error {
	sqlBuilder := sq.Replace(m.TableName()).Columns("cluster_address",
		"backup_host",
		"backup_port",
		"mysql_role",
		"shard_value",
		"backup_id",
		"backup_type",
		"data_schema_grant",
		"is_full_backup",
		"backup_consistent_time",
		"backup_begin_time",
		"backup_end_time",
		"backup_status",
		"mysql_version",
		"file_retention_tag",
		"total_filesize",
		"cluster_id",
		"bk_biz_id",
		"bill_id",
		"binlog_info",
		"extra_fields",
		"file_list",
	)
	/*
		var kafkaObjs []*MysqlBackupResultModel
		aaa := i.([]sinker.ModelSinker)
		for _, a := range aaa {
			kafkaObjs = append(kafkaObjs, a.(*MysqlBackupResultModel))
		}

	*/
	kafkaObjs, ok := i.([]MysqlBackupResultModel)
	if !ok {
		kafkaObjs = []MysqlBackupResultModel{i.(MysqlBackupResultModel)}
	}

	for _, kafkaObj := range kafkaObjs {
		var modelObj = &MysqlBackupResultModel{}
		if err := copier.Copy(modelObj, kafkaObj); err != nil {
			return err
		}
		modelObj.FileList, _ = json.Marshal(kafkaObj.FileList)
		modelObj.BinlogInfo, _ = json.Marshal(kafkaObj.BinlogInfo)
		modelObj.ExtraFields, _ = json.Marshal(kafkaObj.ExtraFields)
		modelObj.BkBizId = kafkaObj.BkBizId

		//err = c.Db.Table(*c.Sinker.RuntimeConfig.Dsn.Table).FirstOrCreate(&modelObj).Error
		sqlBuilder = sqlBuilder.Values(
			modelObj.ClusterAddress,
			modelObj.BackupHost,
			modelObj.BackupPort,
			modelObj.MysqlRole,
			modelObj.ShardValue,
			modelObj.BackupId,
			modelObj.BackupType,
			modelObj.DataSchemaGrant,
			modelObj.IsFullBackup,
			modelObj.BackupConsistentTime,
			modelObj.BackupBeginTime,
			modelObj.BackupEndTime,
			modelObj.BackupStatus,
			modelObj.MysqlVersion,
			modelObj.FileRetentionTag,
			modelObj.TotalFilesize,
			modelObj.ClusterId,
			modelObj.BkBizId,
			modelObj.BillId,
			modelObj.BinlogInfo,
			modelObj.ExtraFields,
			modelObj.FileList,
		)
	}

	sqlStr, sqlArgs, err := sqlBuilder.ToSql()
	if err != nil {
		return err
	}
	err = db.Model(m).Exec(sqlStr, sqlArgs...).Error
	if err != nil {
		slog.Error("replace message",
			slog.Any("msg", err), slog.String("sql", sqlStr), slog.Any("args", sqlArgs))
		//return err
	}
	return nil
}

type BackupMetaFileBase struct {
	// BackupId backup uuid 代表一次备份
	BackupId       string `json:"backup_id" db:"backup_id"`
	BackupType     string `json:"backup_type" db:"backup_type"`
	ClusterId      int    `json:"cluster_id" db:"cluster_id"`
	ClusterAddress string `json:"cluster_address" db:"cluster_address"`
	BackupHost     string `json:"backup_host" db:"backup_host"`
	BackupPort     int    `json:"backup_port" db:"backup_port"`
	MysqlRole      string `json:"mysql_role" db:"mysql_role"`
	// ShardValue 分片 id，仅 spider 有用
	ShardValue int    `json:"shard_value" db:"shard_value"`
	BillId     string `json:"bill_id" db:"bill_id"`
	// BkBizId 被清洗过了
	BkBizId         int    `json:"bk_biz_id" db:"bk_biz_id"`
	MysqlVersion    string `json:"mysql_version" db:"mysql_version"`
	DataSchemaGrant string `json:"data_schema_grant" db:"data_schema_grant"`
	// IsFullBackup 是否包含数据的全备
	IsFullBackup bool `json:"is_full_backup" db:"is_full_backup"`
	// BackupConsistentTime 备份的一致性时间点，逻辑备份是备份开始时间，物理备份是备份结束时间， format time.RFC3339
	BackupConsistentTime time.Time `json:"backup_consistent_time" db:"backup_consistent_time"`
	// BackupBeginTime use time.RFC3339
	BackupBeginTime time.Time `json:"backup_begin_time" db:"backup_begin_time"`
	BackupEndTime   time.Time `json:"backup_end_time" db:"backup_end_time"`

	// ConsistentBackupTime todo 为了字段兼容性，可以删掉
	ConsistentBackupTime time.Time `json:"consistent_backup_time" db:"consistent_backup_time"`
}

type ExtraFields struct {
	BkCloudId        int    `json:"bk_cloud_id" db:"bk_cloud_id"`
	FileRetentionTag string `json:"file_retention_tag" db:"file_retention_tag"`
	TotalFilesize    uint64 `json:"total_filesize" db:"total_filesize"`
	// TotalSizeKBUncompress 压缩前大小，如果是zstd压缩会提供压缩前大小，-1,0 都是无效值。这不是精确大小，可能存在四舍五入
	TotalSizeKBUncompress int64 `json:"total_size_kb_uncompress" db:"total_size_kb_uncompress"`
	EncryptEnable         bool  `json:"encrypt_enable" db:"encrypt_enable"`
	// StorageEngine 物理备份使用
	StorageEngine string `json:"storage_engine" db:"storage_engine"`
	TimeZone      string `json:"time_zone" db:"time_zone"`
	// BackupCharset 逻辑备份使用
	BackupCharset  string `json:"backup_charset" db:"backup_charset"`
	SqlMode        string `json:"sql_mode" db:"sql_mode"`
	BinlogFormat   string `json:"binlog_format" db:"binlog_format"`
	BinlogRowImage string `json:"binlog_row_image" db:"binlog_row_image"`
	// BackupTool command name xtrabackup / mydumper / mysqldump
	BackupTool string `json:"backup_tool" db:"backup_tool"`
}

type BinlogStatusInfo struct {
	// ShowMasterStatus 当前实例 show master status 输出，本机位点
	ShowMasterStatus *StatusInfo `json:"show_master_status"`
	// ShowSlaveStatus 显示的是当前实例的 master 的位点
	ShowSlaveStatus *StatusInfo `json:"show_slave_status"`
}

type StatusInfo struct {
	BinlogFile string `json:"binlog_file"`
	BinlogPos  string `json:"binlog_pos"`
	Gtid       string `json:"gtid"`
	MasterHost string `json:"master_host"`
	MasterPort int    `json:"master_port"`
}

type TarFileItem struct {
	FileName      string   `json:"file_name"`
	FileSize      int64    `json:"file_size"`
	FileType      string   `json:"file_type" enums:"schema,data,metadata,priv"`
	ContainFiles  []string `json:"contain_files"`
	ContainTables []string `json:"contain_tables"`
	// TaskId backup task_id
	TaskId string `json:"task_id"`
}

type IndexContent struct {
	BackupMetaFileBase
	// ExtraFields 这里不能展开
	ExtraFields

	// BinlogInfo show slave status / show master status
	BinlogInfo BinlogStatusInfo `json:"binlog_info" db:"binlog_info"`

	FileList []*TarFileItem `json:"file_list" db:"file_list"`
}
