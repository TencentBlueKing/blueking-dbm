// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package sinker

import (
	"fmt"
	"log/slog"
	"reflect"

	"github.com/go-sql-driver/mysql"
	"github.com/pkg/errors"
	"gorm.io/gorm"
	"gorm.io/gorm/clause"
	"gorm.io/gorm/schema"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/cst"
)

type MysqlWriter struct {
	db          *gorm.DB
	dbWithModel bool
	writeMode   string
	omitFields  []string
}

func NewMysqlWriter(dsn *InstanceDsn, db *gorm.DB) (*MysqlWriter, error) {
	if db != nil {
		return &MysqlWriter{db: db}, nil
	}
	if dsn == nil {
		return nil, errors.New("dsn is nil")
	}
	db, err := GetGormDB(dsn)
	if err != nil {
		return nil, err
	}
	return &MysqlWriter{db: db}, nil
}

func (w *MysqlWriter) Type() string {
	return "mysql"
}

func (w *MysqlWriter) AutoMigrate(m interface{}) error {
	slog.Info("MysqlWriter run common migrate for", slog.Any("model", m))
	return w.db.Migrator().AutoMigrate(m)
	//return nil
}

// OnDuplicate handle one or multi object with unique key
func (w *MysqlWriter) OnDuplicate(objs interface{}) error {
	if w.writeMode == cst.ModeInsertIgnore {
		slog.Info("MysqlWriter ignore duplicate key error", slog.Any("model", objs))
		// w.dbWithModel = w.dbWithModel.Clauses(clause.OnConflict{DoNothing: true})
		return nil
	}
	if w.writeMode == cst.ModeUpsert || w.writeMode == cst.ModeReplace {
		slog.Info("MysqlWriter upsert duplicate key error", slog.Any("model", objs))
		// 是用 model 上的唯一键定义
		return w.db.Clauses(clause.OnConflict{UpdateAll: true}).Create(objs).Error
	}
	return nil
}

func (w *MysqlWriter) WriteBatch(table interface{}, ms interface{}) error {
	var err error
	if w.dbWithModel {
		tableType := reflect.TypeOf(table).Elem().Name()
		if tableType == cst.NoStrictSchemaModel {
			// gorm 处理 table name 是动态生成的有问题，这里要指定 table name, FakeModel 不行
			if tabler, ok := table.(schema.Tabler); ok {
				w.db = w.db.Table(tabler.TableName())
			} else {
				return fmt.Errorf("FakeModelForNoStrictSchema must implement schema.Tabler for table=%+v", table)
			}
		} else {
			w.db = w.db.Model(table)
		}
		// w.omitFields
		if omitted, ok := table.(base.ModelFieldOmit); ok {
			w.db = w.db.Omit(omitted.OmitFields()...)
		}
		w.dbWithModel = true
	}
	err = w.db.Create(ms).Error
	var mysqlErr *mysql.MySQLError

	if err != nil { // create
		if (errors.As(err, &mysqlErr) && mysqlErr.Number != 1062) && !errors.Is(err, gorm.ErrDuplicatedKey) {
			return err
		}
		slog.Warn("MysqlWriter insert duplicate key error", slog.Any("err", err))
		if txErr := w.OnDuplicate(ms); txErr != nil {
			return errors.WithMessage(err, txErr.Error())
		}
	}
	return nil
}

func (w *MysqlWriter) GormDB() *gorm.DB {
	return w.db
}

func (w *MysqlWriter) CloseGormDB() error {
	db, _ := w.db.DB()
	return db.Close()
}

func (w *MysqlWriter) DB() base.DbExec {
	db, _ := w.db.DB()
	return db
}

func (w *MysqlWriter) SetWriteMode(mode string) {
	w.writeMode = mode
}
func (w *MysqlWriter) GetWriteMode() string {
	return w.writeMode
}
