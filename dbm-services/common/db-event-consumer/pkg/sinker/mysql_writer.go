// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package sinker

import (
	"log/slog"

	"github.com/pkg/errors"
	"gorm.io/gorm"
)

type MysqlWriter struct {
	db *gorm.DB
}

func NewMysqlWriter(dsn *InstanceDsn, db *gorm.DB) (*MysqlWriter, error) {
	if db != nil {
		return &MysqlWriter{db: db}, nil
	}
	if dsn == nil {
		return nil, errors.New("dsn is nil")
	}
	db, err := GetGormDB(dsn, nil)
	if err != nil {
		return nil, err
	}
	return &MysqlWriter{db: db}, nil
}

func (w *MysqlWriter) Type() string {
	return "mysql"
}

func (w *MysqlWriter) AutoMigrate(m interface{}) error {
	slog.Info("MysqlWriter run common migrate for ", m)
	return w.db.Migrator().AutoMigrate(m)
	//return nil
}

func (w *MysqlWriter) WriteOne(obj interface{}) error {
	if omitted, ok := obj.(ModelFieldOmit); ok {
		return w.db.Omit(omitted.OmitFields()...).Create(obj).Error
	} else {
		return w.db.Create(obj).Error
	}
}

func (w *MysqlWriter) Write2(tableName string, objs interface{}) error {
	return w.db.Table(tableName).Create(objs).Error
}

func (w *MysqlWriter) CustomWrite(m interface{}, f func(i interface{}, db *gorm.DB) error) error {
	// func(interface{}, sinker.DSWriter)
	if f != nil {
		return f(m, w.db)
	}
	return w.db.Save(m).Error
	//return nil
}

func (w *MysqlWriter) WriteBatch(table interface{}, ms interface{}) error {
	if omitted, ok := table.(ModelFieldOmit); ok {
		return w.db.Model(table).Omit(omitted.OmitFields()...).Create(ms).Error
	} else {
		return w.db.Model(table).Create(ms).Error
	}
}

func (w *MysqlWriter) GormDB() *gorm.DB {
	return w.db
}
