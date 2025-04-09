// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysql_backup_result

import (
	"time"
)

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
