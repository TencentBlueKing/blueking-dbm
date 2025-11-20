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
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
)

type MysqlBackupStatusModel struct {
	base.BaseModel         `json:",inline" gorm:"embedded" xorm:"extends"`
	dbareport.BackupStatus `json:",inline" xorm:"extends"`
}

func (m MysqlBackupStatusModel) TableName() string {
	return "tb_mysql_backup_progress"
}

func (m MysqlBackupStatusModel) UniqueKey() []string {
	return []string{"event_uuid"}
}

func (m MysqlBackupStatusModel) MigrateSchema(w base.DSWriter) error {
	slog.Info("run migrate for MysqlBackupStatusModel", slog.String("table", m.TableName()))
	if w.Type() == "mysql" || w.Type() == "mysql_raw" {
		dbWriter, ok := w.(base.GormMigrator)
		if !ok {
			return errors.Errorf("writer_type=%s has no gorm db for custom migrate: %s", w.Type(), m.TableName())
		}
		db := dbWriter.GormDB()

		// 处理字段
		if err := db.Migrator().AutoMigrate(&m); err != nil {
			return err
		}

		// 处理约束与索引
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "uk_eventuuid",
			[]string{"event_uuid"}, true, true); err != nil {
			return err
		}
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_clusterstatus",
			[]string{"cluster_domain", "status"}, false, true); err != nil {
			return err
		}
		if err := base.CreateOrUpdateIndex(db, m.TableName(), "idx_clusteridstatus",
			[]string{"cluster_id", "status"}, false, true); err != nil {
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
