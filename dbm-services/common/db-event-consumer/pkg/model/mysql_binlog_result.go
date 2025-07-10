// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

type BinlogFileModel struct {
	BaseModel `xorm:"extends"`

	BkBizId   int `json:"bk_biz_id,omitempty" db:"bk_biz_id" gorm:"column:bk_biz_id;type:varchar(32);NOT NULL;index:id_bkbizid,priority:1"`
	ClusterId int `json:"cluster_id,omitempty" db:"cluster_id" gorm:"column:cluster_id;type:int;NOT NULL;index:id_clusterid,priority:1"`
	// immutable domain, 如果是从库，也使用主域名。cluster_domain 至少作为备注信息，一般不作为查询条件
	ClusterDomain string `json:"cluster_domain" db:"cluster_domain" gorm:"column:cluster_domain;type:varchar(32);NOT NULL;index:uk_cluster,unique,priority:1"`
	DbRole        string `json:"db_role" db:"db_role" gorm:"column:db_role;type:varchar(32);NOT NULL"`
	Host          string `json:"host,omitempty" db:"host" gorm:"column:host;type:varchar(32);NOT NULL;index:uk_cluster,unique,priority:2"`
	Port          int    `json:"port,omitempty" db:"port" gorm:"column:port;type:int;NOT NULL;index:uk_cluster,unique,priority:3;index:idx_host"`
	Filename      string `json:"filename,omitempty" db:"filename" gorm:"column:filename;type:varchar(32);NOT NULL;index:uk_cluster,unique,priority:4"`
	Filesize      int64  `json:"size" db:"filesize" gorm:"column:filesize;type:bigint;NOT NULL"`
	// FileMtime 文件最后修改时间，带时区
	FileMtime        string `json:"file_mtime" db:"file_mtime" gorm:"column:file_mtime;type:datetime;NOT NULL;index:idx_mtime;index:id_clusterid,priority:2"`
	StartTime        string `json:"start_time" db:"start_time" gorm:"column:start_time;type:datetime;NOT NULL"`
	StopTime         string `json:"stop_time" db:"stop_time" gorm:"column:stop_time;type:datetime;NOT NULL"`
	BackupEnable     bool   `json:"backup_enable" db:"backup_enable" gorm:"column:backup_enable;type:tinyint;NOT NULL"`
	BackupStatus     int    `json:"backup_status,omitempty" db:"backup_status" gorm:"column:backup_status;type:tinyint;NOT NULL;index:idx_status"`
	BackupStatusInfo string `json:"backup_status_info" db:"backup_status_info" gorm:"column:backup_status_info;type:varchar(32);NOT NULL"`
	TaskId           string `json:"task_id,omitempty" db:"task_id" gorm:"column:task_id;type:varchar(32);NOT NULL;index:idx_taskid"`
	FileRetentionTag string `json:"file_retention_tag" db:"file_retention_tag" gorm:"column:file_retention_tag;type:varchar(32);NOT NULL"`
}

func (m BinlogFileModel) TableName() string {
	return "tb_mysql_binlog_result"
}
