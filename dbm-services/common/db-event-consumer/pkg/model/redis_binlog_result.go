// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import (
	"time"

	"dbm-services/common/db-event-consumer/pkg/base"
)

/*
{"report_type":"redis_binlogbackup","bk_biz_id":"00002","bk_cloud_id":0,
"server_ip":"1.2.3.79","server_port":30009,"domain":"2.a.1.db",
"db_type":"TendisSSDInstance","role":"slave",
"backup_dir":"/data/dbbak/binlog/30009","backup_file":"/data/dbbak/binlog/30009/binlog-1.3.3.79-30009-0014018-20251216171048.log.zst",
"kvstoreidx":0,"backup_file_size":3649228,"time_zone":"CST","backup_taskid":"26208491383",
"backup_md5":"","backup_tag":"REDIS_BINLOG","shard_value":"7875-8749",
"status":"to_backup_system_start","message":"上传备份系统中","start_time":"2025-12-16T17:10:48+08:00","end_time":"2025-12-16T17:31:20+08:00"}

{"report_type":"redis_binlogbackup","bk_biz_id":"00002","bk_cloud_id":0,
"server_ip":"1.1.2.214","server_port":30000,"domain":"z.x.b.db",
"db_type":"TendisplusInstance","role":"slave",
"backup_dir":"/data/dbbak/binlog/30000","backup_file":"/data/dbbak/binlog/30000/binlog-1.2.1.214-30000-5-0022670-20251216171459.log.zst",
"kvstoreidx":5,"backup_file_size":2712382,"time_zone":"CST","backup_taskid":"26208498264",
"backup_md5":"","backup_tag":"REDIS_BINLOG","shard_value":"15236-15528",
"status":"to_backup_system_start","message":"上传备份系统中","start_time":"2025-12-16T17:14:59+08:00","end_time":"2025-12-16T17:34:59+08:00"}

*/

type RedisBinlogFileModel struct {
	base.BaseModel `json:",inline" gorm:"embedded" xorm:"extends"`

	BackupType   string `json:"report_type" db:"backup_type" gorm:"column:backup_type;type:varchar(32);NOT NULL"`
	ImmuteDomain string `json:"domain" db:"immute_domain" gorm:"column:immute_domain;type:varchar(255);NOT NULL;index:uk_cluster,unique,priority:1"`
	BackupHost   string `json:"server_ip" db:"backup_ip" gorm:"column:backup_ip;type:varchar(32);NOT NULL;index:uk_cluster,unique,priority:2"`
	BackupPort   int    `json:"server_port" db:"backup_port" gorm:"column:backup_port;type:int;NOT NULL;index:uk_cluster,unique,priority:3"`
	KvStoreIdx   int    `json:"kvstoreidx" db:"kvstoreidx" gorm:"column:kvstoreidx;type:int;NOT NULL;index:uk_cluster,unique,priority:4"`
	InstRole     string `json:"role" db:"redis_role" gorm:"column:redis_role;type:varchar(32);NOT NULL"`
	DbType       string `json:"db_type" db:"redis_type" gorm:"column:redis_type;type:varchar(32);NOT NULL"`
	// BillId          string `json:"bill_id" db:"bill_id" gorm:"column:bill_id;type:varchar(32);NOT NULL"`
	BkBizId string `json:"bk_biz_id" db:"bk_biz_id" gorm:"column:bk_biz_id;type:varchar(32);NOT NULL"`
	// MysqlVersion    string `json:"mysql_version" db:"mysql_version" gorm:"column:mysql_version;type:varchar(120);NOT NULL"`

	BackupTaskID   uint64 `json:"backup_taskid" db:"backup_taskid" gorm:"column:backup_taskid;type:bigint;NOT NULL"`
	BackupFilesize uint64 `json:"backup_file_size" db:"backup_file_size" gorm:"column:backup_file_size;type:bigint;NOT NULL"`
	BackupFileName string `json:"backup_file" db:"backup_file" gorm:"column:backup_file;type:varchar(255);NOT NULL"`

	ShardValue string `json:"shard_value" db:"shard_value" gorm:"column:shard_value;type:varchar(255)"`
	BackupTag  string `json:"backup_tag" db:"backup_tag" gorm:"column:backup_tag;type:varchar(255);NOT NULL"`

	BackupBeginTime time.Time `json:"start_time" db:"backup_begin_time" gorm:"column:backup_begin_time;type:TIMESTAMP NULL;default:null"`
	BackupEndTime   time.Time `json:"end_time" db:"backup_end_time" gorm:"column:backup_end_time;type:TIMESTAMP NULL;default:null"`
	BackupStatus    int       `json:"status,omitempty" db:"backup_status" gorm:"column:backup_status;type:tinyint;NOT NULL"`
}

func (m RedisBinlogFileModel) TableName() string {
	return "tb_redis_binlog_result"
}

// UniqueKey is used to handle duplicate record
func (m RedisBinlogFileModel) UniqueKey() []string {
	return []string{"backup_ip", "backup_port", "kvstoreidx", "backup_file"}
}
