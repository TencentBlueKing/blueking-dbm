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

	"github.com/pkg/errors"
)

// MysqlPartitionResultModel MySQL分区结果模型
type MysqlPartitionResultModel struct {
	base.BaseModel `json:",inline" gorm:"embedded" xorm:"extends"`

	// 云区域ID
	BkCloudId int `json:"bk_cloud_id,omitempty" db:"bk_cloud_id" gorm:"column:bk_cloud_id;type:int;NOT NULL"`
	// 业务ID
	BkBizId int `json:"bk_biz_id,omitempty" db:"bk_biz_id" gorm:"column:bk_biz_id;type:int;NOT NULL"`
	// 集群类型
	ClusterType string `json:"cluster_type,omitempty" db:"cluster_type" gorm:"column:cluster_type;type:varchar(32);NOT NULL"`
	// 配置ID
	ConfigId int `json:"config_id,omitempty" db:"config_id" gorm:"column:config_id;type:int;NOT NULL"`
	// 创建时间
	CreateTime time.Time `json:"create_time" db:"create_time" gorm:"column:create_time;type:TIMESTAMP;default:CURRENT_TIMESTAMP"`
	// 状态
	Status string `json:"status,omitempty" db:"status" gorm:"column:status;type:varchar(32);NOT NULL"`
	// 日志信息
	ExecLog string `json:"exec_log,omitempty" db:"exec_log" gorm:"column:exec_log;type:text;NOT NULL"`
}

// TableName 返回表名
func (m MysqlPartitionResultModel) TableName() string {
	return "tb_mysql_partition_result"
}

// MigrateSchema 自定义表结构迁移
func (m *MysqlPartitionResultModel) MigrateSchema(w base.DSWriter) error {
	if w.Type() == "mysql" || w.Type() == "mysql_raw" {
		dbWriter, ok := w.(base.GormMigrator)
		if !ok {
			return errors.Errorf("writer_type=%s has no gorm db for custom migrate: %s", w.Type(), m.TableName())
		}
		db := dbWriter.GormDB()

		// 调用通用 migrate
		if err := db.Migrator().AutoMigrate(&m); err != nil {
			return err
		}

		// 1) create_time
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_createtime",
			[]string{"create_time"}, false, true); err != nil {
			return err
		}
		// 2) status, create_time
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_status_createtime",
			[]string{"status", "create_time"}, false, true); err != nil {
			return err
		}
		// 3) config_id, status
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_configid_status",
			[]string{"config_id", "status"}, false, true); err != nil {
			return err
		}
		// 4) config_id, create_time
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_configid_createtime",
			[]string{"config_id", "create_time"}, false, true); err != nil {
			return err
		}
		// 5) bk_biz_id, config_id, cluster_type
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_bkbizid_configid_clustertype",
			[]string{"bk_biz_id", "config_id", "cluster_type"}, false, true); err != nil {
			return err
		}
		return nil
	} else {
		return w.AutoMigrate(m)
	}
}
