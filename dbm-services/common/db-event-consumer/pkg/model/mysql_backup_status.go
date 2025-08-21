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

	"dbm-services/common/db-event-consumer/pkg/sinker"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/dbareport"
)

type MysqlBackupStatusModel struct {
	BaseModel              `json:",inline" gorm:"embedded" xorm:"extends"`
	dbareport.BackupStatus `json:",inline" xorm:"extends"`
}

func (m MysqlBackupStatusModel) TableName() string {
	return "tb_mysql_backup_progress"
}

func (m MysqlBackupStatusModel) MigrateSchema(w sinker.DSWriter) error {
	slog.Info("run migrate for MysqlBackupStatusModel", slog.String("table", m.TableName()))
	if w.Type() == "mysql" {
		dbWriter := w.(*sinker.MysqlWriter)
		db := dbWriter.GormDB()
		if err := db.Migrator().AutoMigrate(&m); err != nil {
			return err
		}
		if err := CreateOrUpdateIndex(db, m.TableName(), "idx_cluster",
			[]string{"cluster_domain"}, false, true); err != nil {
			return err
		}
		if err := CreateOrUpdateIndex(db, m.TableName(), "idx_status",
			[]string{"status"}, false, true); err != nil {
			return err
		}
		if err := CreateOrUpdateIndex(db, m.TableName(), "idx_host",
			[]string{"backup_host"}, false, true); err != nil {
			return err
		}
		return nil
	} else if w.Type() == "mysql_xorm" {
		return w.AutoMigrate(m)
	} else {
		return w.AutoMigrate(m)
	}
}

// replace
