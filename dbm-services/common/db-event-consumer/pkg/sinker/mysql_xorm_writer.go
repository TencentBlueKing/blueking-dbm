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
	"xorm.io/xorm"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/cst"
	"dbm-services/common/go-pubpkg/cmutil"
)

type XormWriter struct {
	engine      *xorm.Engine
	session     *xorm.Session
	dbWithModel bool
	writeMode   string
}

func NewXormWriter(dsn *InstanceDsn, engine *xorm.Engine) (*XormWriter, error) {
	if engine != nil {
		return &XormWriter{engine: engine}, nil
	}
	if dsn == nil {
		return nil, errors.New("dsn is nil")
	}

	engine, err := GetXormDB(dsn)
	if err != nil {
		return nil, err
	}
	return &XormWriter{engine: engine}, nil
}

func (w *XormWriter) Type() string {
	return "mysql_xorm"
}

func (w *XormWriter) AutoMigrate(m interface{}) error {
	slog.Info("XormWriter run common migrate for ", m)

	_, err := w.engine.SyncWithOptions(xorm.SyncOptions{IgnoreDropIndices: true})
	return err
}

// onOneDuplicate handle one object with unique key
func (w *XormWriter) onOneDuplicate(obj interface{}, sess *xorm.Session) error {
	var err error
	uniqueWhere := make(map[string]interface{})
	if uniqueCols, ok := obj.(base.UniqueKey); ok {
		uniqueWhere = cmutil.StructToMap(obj, "db", uniqueCols.UniqueKey())
	}
	if len(uniqueWhere) == 0 {
		return errors.WithMessagef(err, "failed to find unique key to upsert for %+v", obj)
	}

	if w.writeMode == cst.ModeUpsert {
		if _, err = sess.Where(uniqueWhere).Limit(1).Update(obj); err != nil {
			return err
		}
	} else if w.writeMode == cst.ModeReplace {
		sess.Begin()
		txErr := func() error {
			if _, err := sess.Where(uniqueWhere).Limit(1).Delete(obj); err != nil {
				return err
			}
			if _, err := sess.Insert(obj); err != nil {
				return err
			}
			return nil
		}
		if txErr != nil {
			_ = sess.Rollback()
		} else {
			return sess.Commit()
		}
	}
	return nil
}

func (w *XormWriter) WriteBatch(table interface{}, ms interface{}) error {
	// xorm table allow &{}, or table name string
	var err error
	if !w.dbWithModel {
		w.session = w.engine.Table(table)
		if omitted, ok := table.(base.ModelFieldOmit); ok {
			w.session = w.session.Omit(omitted.OmitFields()...)
		}
		w.dbWithModel = true
	}
	_, err = w.session.InsertMulti(ms)
	var mysqlErr *mysql.MySQLError
	if err != nil { // create, 不能丢失这个原始 error
		if (errors.As(err, &mysqlErr) && mysqlErr.Number != 1062) && !errors.Is(err, gorm.ErrDuplicatedKey) {
			return err
		}
		slog.Warn("XormWriter insert duplicate key error", slog.Any("err", err))
		if txErr := w.OnDuplicate(ms); txErr != nil {
			return errors.WithMessage(err, txErr.Error())
		}
	}
	return nil
}

// OnDuplicate handle one or multi object with unique key
func (w *XormWriter) OnDuplicate(objs interface{}) error {
	if w.writeMode == cst.ModeInsertIgnore {
		slog.Info("XormWriter ignore duplicate key error", slog.Any("model", objs))
		return nil
	}
	if w.writeMode == cst.ModeUpsert || w.writeMode == cst.ModeReplace {
		slog.Info("XormWriter upsert duplicate key error", slog.Any("model", objs))
		sliceValue := reflect.Indirect(reflect.ValueOf(objs))
		if sliceValue.Kind() != reflect.Slice {
			return errors.New("needs a pointer to a slice")
		}
		w.session.Begin()
		txErr := func(sess *xorm.Session) error {
			var err error
			for i := 0; i < sliceValue.Len(); i++ {
				obj := sliceValue.Index(i).Interface()
				if sess == nil {
					return errors.New("session is nil")
				}
				fmt.Printf("sess i=%d\n", i)
				if _, err = sess.InsertMulti(obj); err == nil {
					continue
				}
				if err = w.onOneDuplicate(obj, sess); err != nil {
					return err
				}
			}
			return nil
		}(w.session)
		if txErr != nil {
			_ = w.session.Rollback()
			return txErr
		} else {
			return w.session.Commit()
		}
	}
	return nil
}
func (w *XormWriter) DB() base.DbExec {
	return w.engine.DB().DB
}

func (w *XormWriter) SetWriteMode(mode string) {
	w.writeMode = mode
}
func (w *XormWriter) GetWriteMode() string {
	return w.writeMode
}

func buildUniqueColumns(uniqueKey []string) []clause.Column {
	columns := make([]clause.Column, len(uniqueKey))
	for _, key := range uniqueKey {
		columns = append(columns, clause.Column{Name: key})
	}
	return columns
}
