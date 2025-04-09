// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysql_backup_result

import (
	"encoding/json"
	"fmt"
	"time"
)

type ModelBackupReport struct {
	ID        uint64    `gorm:"primaryKey;autoIncrement:true"`
	CreatedAt time.Time `json:"created_at" db:"created_at"`
	UpdatedAt time.Time `json:"updated_at" db:"updated_at"`

	BackupId        string `json:"backup_id" db:"backup_id"`
	BackupType      string `json:"backup_type" db:"backup_type"`
	ClusterId       int    `json:"cluster_id" db:"cluster_id"`
	ClusterAddress  string `json:"cluster_address" db:"cluster_address"`
	BackupHost      string `json:"backup_host" db:"backup_host"`
	BackupPort      int    `json:"backup_port" db:"backup_port"`
	MysqlRole       string `json:"mysql_role" db:"mysql_role"`
	ShardValue      int    `json:"shard_value" db:"shard_value"`
	BillId          string `json:"bill_id" db:"bill_id"`
	BkBizId         int    `json:"bk_biz_id" db:"bk_biz_id"`
	MysqlVersion    string `json:"mysql_version" db:"mysql_version"`
	DataSchemaGrant string `json:"data_schema_grant" db:"data_schema_grant"`
	// IsFullBackup 是否包含数据的全备
	IsFullBackup     bool   `json:"is_full_backup" db:"is_full_backup"`
	FileRetentionTag string `json:"file_retention_tag" db:"file_retention_tag"`
	TotalFilesize    uint64 `json:"total_filesize" db:"total_filesize"`

	BackupConsistentTime time.Time       `json:"backup_consistent_time" db:"backup_consistent_time"`
	BackupBeginTime      time.Time       `json:"backup_begin_time" db:"backup_begin_time"`
	BackupEndTime        time.Time       `json:"backup_end_time" db:"backup_end_time"`
	BinlogInfo           json.RawMessage `json:"binlog_info" db:"binlog_info"`
	FileList             json.RawMessage `json:"file_list" db:"file_list"`
	ExtraFields          json.RawMessage `json:"extra_fields" db:"extra_fields"`
	/*
		// BinlogInfo show slave status / show master status
		BinlogInfo BinlogStatusInfo `json:"binlog_info" db:"binlog_info"`
		// FileList backup tar file list
		FileList     []TarFileItem `json:"file_list" db:"file_list"`
		ExtraFields  ExtraFields   `json:"extra_fields" db:"extra_fields"`
	*/
	BackupStatus string `json:"backup_status" db:"backup_status"`
}

func (m ModelBackupReport) TableName() string {
	return "tb_mysql_backup_result"
}

func (m ModelBackupReport) Key() string {
	return fmt.Sprintf("{cluster_address=%s,backup_host=%s,backup_port=%d,backup_id=%s,time=%s}",
		m.ClusterAddress, m.BackupHost, m.BackupPort, m.BackupId, m.BackupConsistentTime.Format("2006-01-02 15:04:05"))
}
