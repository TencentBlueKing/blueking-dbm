// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import "time"

type MysqlTableSize struct {
	ID uint `gorm:"primaryKey;autoIncrement:true"`
	// TheDate 20250101
	TheDate int `gorm:"column:thedate;type:int;not null" json:"thedate" db:"thedate"`
	// DtEventTimeStamp 1577836800000
	DtEventTimeStamp int64 `gorm:"column:dteventtimestamp;type:bigint;not null" json:"dteventtimestamp" db:"dteventtimestamp"`
	// DtEventTimeHour	'2020-01-01 01:00:00'
	DtEventTimeHour string `gorm:"column:dteventtimehour;type:varchar(127);not null" json:"dteventtimehour" db:"dteventtimehour"`
	// ReportTime	'2020-01-01 01:02:03'
	ReportTime       time.Time `gorm:"column:report_time;type:varchar(127);not null" json:"report_time" db:"report_time"`
	BkCloudId        int       `gorm:"column:bk_cloud_id;type:int;not null" json:"bk_cloud_id" db:"bk_cloud_id"`
	BkBizId          int       `gorm:"column:bk_biz_id;type:int;not null" json:"bk_biz_id" db:"bk_biz_id"`
	ClusterDomain    string    `gorm:"column:cluster_domain;type:varchar(127);not null" json:"cluster_domain" db:"cluster_domain"`
	InstanceHost     string    `gorm:"column:instance_host;type:varchar(127);not null" json:"instance_host" db:"instance_host"`
	InstancePort     int       `gorm:"column:instance_port;type:int;not null" json:"instance_port" db:"instance_port"`
	InstanceRole     string    `gorm:"column:instance_role;type:varchar(127);not null" json:"instance_role" db:"instance_role"`
	MachineType      string    `gorm:"column:machine_type;type:varchar(127);not null" json:"machine_type" db:"machine_type"`
	OriginalDatabase string    `gorm:"column:original_database_name;type:varchar(127);not null" json:"original_database_name" db:"original_database_name"`
	Database         string    `gorm:"column:database_name;type:varchar(127);not null" json:"database_name" db:"database_name"`
	Table            string    `gorm:"column:table_name;type:varchar(127);not null" json:"table_name" db:"table_name"`
	DatabaseSize     int64     `gorm:"column:database_size;type:bigint;not null" json:"database_size" db:"database_size"`
	TableSize        int64     `gorm:"column:table_size;type:bigint;not null" json:"table_size" db:"table_size"`
}

func (MysqlTableSize) TableName() string {
	return "mysql_table_size"
}
