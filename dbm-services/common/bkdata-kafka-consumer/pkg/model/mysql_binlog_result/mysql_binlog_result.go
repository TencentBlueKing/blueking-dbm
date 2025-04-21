// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package mysql_binlog_result

type BinlogFileModel struct {
	BkBizId   int `json:"bk_biz_id,omitempty" db:"bk_biz_id"`
	ClusterId int `json:"cluster_id,omitempty" db:"cluster_id"`
	// immutable domain, 如果是从库，也使用主域名。cluster_domain 至少作为备注信息，一般不作为查询条件
	ClusterDomain string `json:"cluster_domain" db:"cluster_domain"`
	DBRole        string `json:"db_role" db:"db_role"`
	Host          string `json:"host,omitempty" db:"host"`
	Port          int    `json:"port,omitempty" db:"port"`
	Filename      string `json:"filename,omitempty" db:"filename"`
	Filesize      int64  `json:"size" db:"filesize"`
	// FileMtime 文件最后修改时间，带时区
	FileMtime        string `json:"file_mtime" db:"file_mtime"`
	StartTime        string `json:"start_time" db:"start_time"`
	StopTime         string `json:"stop_time" db:"stop_time"`
	BackupEnable     bool   `json:"backup_enable" db:"backup_enable"`
	BackupStatus     int    `json:"backup_status,omitempty" db:"backup_status"`
	BackupStatusInfo string `json:"backup_status_info" db:"backup_status_info"`
	TaskId           string `json:"task_id,omitempty" db:"task_id"`
	FileRetentionTag string `json:"file_retention_tag" db:"file_retention_tag"`
}
