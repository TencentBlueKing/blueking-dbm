// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package sinker

import (
	"context"
	"log/slog"
	"reflect"
	"time"

	"github.com/gogf/gf/v2/database/gdb"
	"github.com/gogf/gf/v2/util/gconv"
	sb "github.com/huandu/go-sqlbuilder"
	"github.com/pkg/errors"
	"github.com/samber/lo"
	"gorm.io/gorm"
	"gorm.io/gorm/schema"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/cst"
)

func NewDorisWriter(dsn *InstanceDsn) (*DorisWriter, error) {
	if dsn == nil {
		return nil, errors.New("dsn is nil")
	}
	db, err := GetGoframeDB(dsn)
	if err != nil {
		return nil, err
	}
	dbForMigrate, err := GetGormDB(dsn)
	if err != nil {
		return nil, err
	}
	return &DorisWriter{db: db, dbGorm: dbForMigrate}, nil
}

type DorisWriter struct {
	dbGorm      *gorm.DB
	db          gdb.DB
	session     *gdb.Model
	dbWithModel bool
	writeMode   string
	dbParseTime bool
}

func (w *DorisWriter) Type() string {
	return "doris"
}
func (w *DorisWriter) AutoMigrate(m interface{}) error {
	slog.Info("DorisWriter run common migrate for", slog.Any("model", m))
	err := w.dbGorm.Migrator().AutoMigrate(m)
	/*
		_ = func() error {
			db, _ := w.dbGorm.DB()
			return db.Close()
		}
	*/
	return err
}

// WriteBatch goframe 版本，支持 replace 语义
func (w *DorisWriter) WriteBatch(table interface{}, models interface{}) error {
	var err error
	if !w.dbWithModel {
		w.session = w.db.Model(table)
		w.dbWithModel = true
	}
	if omitted, ok := table.(base.ModelFieldOmit); ok {
		w.session = w.db.Model(table).FieldsEx(omitted.OmitFields()).Data(models)
	} else {
		w.session = w.db.Model(table).Data(models)
	}
	if w.writeMode == cst.ModeUpsert || w.writeMode == cst.ModeReplace {
		_, err = w.session.Replace()
	} else {
		_, err = w.session.InsertIgnore()
	}
	return err
}

// WriteBatch2 把 struct 都转成 map 处理
func (w *DorisWriter) WriteBatch2(table interface{}, models interface{}) error {
	var err error
	var objs []map[string]interface{}
	sliceValue := reflect.Indirect(reflect.ValueOf(models))
	if sliceValue.Kind() == reflect.Slice {
		canMap := false
		firstObj := sliceValue.Index(0)
		if firstObj.Kind() == reflect.Struct {
			canMap = true
		} else if firstObj.Kind() == reflect.Ptr && firstObj.Elem().Kind() == reflect.Struct {
			canMap = true
		}
		if canMap {
			for i := 0; i < sliceValue.Len(); i++ {
				obj := sliceValue.Index(i).Interface()
				m := gconv.Map(obj, gconv.MapOption{
					Tags: []string{"db"},
				})
				objs = append(objs, m)
			}
		} else {
			if err = gconv.Scan(models, &objs); err != nil {
				return errors.WithMessagef(err, "gconv.Scan failed for models %+v", models)
			}
		}
	} else {
		m := gconv.Map(models, gconv.MapOption{
			Tags: []string{"db"},
		})
		objs = append(objs, m)
	}

	// 换用 sql builder 处理
	if err = w.writeDbUsingMapWithSqlBuilderBatch(table, objs); err != nil {
		return err
	}

	return nil
}

// writeDbUsingMapWithSqlBuilderBatch use sql builder to generate sql
func (w *DorisWriter) writeDbUsingMapWithSqlBuilderBatch(table interface{}, objs []map[string]interface{}) error {
	t, ok := table.(schema.Tabler)
	if !ok {
		return errors.Errorf("Cannot find TableName() for table %v", table)
	}
	builder := sb.NewInsertBuilder()
	if w.writeMode == cst.ModeUpsert || w.writeMode == cst.ModeReplace {
		builder.ReplaceInto(t.TableName())
	} else {
		builder.InsertIgnoreInto(t.TableName())
	}
	colNames := lo.Keys(objs[0])
	builder.Cols(colNames...)
	colValues := convertMapSliceToSliceSliceWithKeys(objs, colNames, w.dbParseTime)
	for _, vals := range colValues {
		builder.Values(vals...)
	}

	sqlStr, sqlArgs := builder.Build()
	sqlFull, err := sb.MySQL.Interpolate(sqlStr, sqlArgs)
	if err != nil {
		return err
	}
	if _, err = w.db.Exec(context.Background(), sqlFull); err != nil {
		return err
	}

	return nil
}

// writeDbUsingMapWithSqlBuilder use sql builder to generate sql
// insert one by one
func (w *DorisWriter) writeDbUsingMapWithSqlBuilder(table interface{}, objs []map[string]interface{}) error {
	t, ok := table.(schema.Tabler)
	if !ok {
		return errors.Errorf("Cannot find TableName() for table %v", table)
	}
	for _, obj := range objs {
		builder := sb.NewInsertBuilder()
		if w.writeMode == cst.ModeUpsert || w.writeMode == cst.ModeReplace {
			builder.ReplaceInto(t.TableName())
		} else {
			builder.InsertIgnoreInto(t.TableName())
		}

		var colNames []string
		var colValues []interface{}
		for colName, colValue := range obj {
			colNames = append(colNames, colName)
			if t, ok := colValue.(time.Time); ok && w.dbParseTime {
				colValues = append(colValues, t.UTC())
			} else {
				colValues = append(colValues, colValue)
			}
		}
		builder.Cols(colNames...)
		builder.Values(colValues...)

		sqlStr, sqlArgs := builder.Build()
		sqlFull, err := sb.MySQL.Interpolate(sqlStr, sqlArgs)
		if err != nil {
			return err
		}
		if _, err = w.db.Exec(context.Background(), sqlFull); err != nil {
			return err
		}
	}
	return nil
}
func (w *DorisWriter) OnDuplicate(objs interface{}) error {
	return nil
}

func (w *DorisWriter) SetWriteMode(mode string) {
	w.writeMode = mode
}
func (w *DorisWriter) GetWriteMode() string {
	return w.writeMode
}

func (w *DorisWriter) GormDB() *gorm.DB {
	return w.dbGorm
}
func (w *DorisWriter) CloseGormDB() error {
	db, _ := w.dbGorm.DB()
	return db.Close()
}

func (w *DorisWriter) DB() base.DbExec {
	db, _ := w.dbGorm.DB()
	return db
}
