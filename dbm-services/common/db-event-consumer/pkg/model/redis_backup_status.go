// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package model

import (
	"log/slog"

	"github.com/pkg/errors"

	"dbm-services/common/db-event-consumer/pkg/base"
)

type RedisBackupStatus struct {
	Status string `json:"status" gorm:"type:varchar(32);NOT NULL"`
	// StatusDetail 如果失败，记录失败详情
	StatusDetail string `json:"status_detail" gorm:"type:text"`

	BackupId   string `json:"backup_task_id" gorm:"type:varchar(60);NOT NULL"`
	BackupType string `json:"backup_type"  gorm:"type:varchar(32);NOT NULL"`

	ImmuteDomain string `json:"immute_domain" gorm:"type:varchar(255);NOT NULL"`
	BackupHost   string `json:"backup_host"  gorm:"type:varchar(32);NOT NULL"`
	BackupPort   int    `json:"backup_port"  gorm:"type:int;NOT NULL"`
	RedisRole    string `json:"redis_role"  gorm:"type:varchar(32);NOT NULL"`

	ShardValue int    `json:"shard_value"  gorm:"type:int;NOT NULL"`
	BkBizId    string `json:"bk_biz_id"  gorm:"type:int;NOT NULL"`
	// IsFullBackup 是否包含数据的全备
	IsFullBackup bool `json:"is_full_backup"  gorm:"type:tinyint"`
}

type RedisBackupStatusModel struct {
	base.BaseModel    `json:",inline" gorm:"embedded" xorm:"extends"`
	RedisBackupStatus `json:",inline" xorm:"extends"`
}

func (m RedisBackupStatusModel) TableName() string {
	return "tb_redis_backup_progress"
}

func (m RedisBackupStatusModel) UniqueKey() []string {
	return []string{"event_uuid"}
}

func (m RedisBackupStatusModel) MigrateSchema(w base.DSWriter) error {
	slog.Info("run migrate for RedisBackupStatusModel", slog.String("table", m.TableName()))
	if w.Type() == "mysql" || w.Type() == "mysql_raw" {
		dbWriter, ok := w.(base.GormMigrator)
		if !ok {
			return errors.Errorf("writer_type=%s has no gorm db for custom migrate: %s", w.Type(), m.TableName())
		}
		db := dbWriter.GormDB()

		// 处理普通字段/索引。(不会删除索引，字段)
		if err := db.Migrator().AutoMigrate(&m); err != nil {
			return err
		}
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_clusterstatus",
			[]string{"immute_domain", "status"}, false, true); err != nil {
			return err
		}
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_status",
			[]string{"status"}, false, true); err != nil {
			return err
		}
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_host",
			[]string{"backup_host"}, false, true); err != nil {
			return err
		}
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_create_ts",
			[]string{"event_create_timestamp"}, false, true); err != nil {
			return err
		}
		return nil
	} else {
		return w.AutoMigrate(m)
	}
}
