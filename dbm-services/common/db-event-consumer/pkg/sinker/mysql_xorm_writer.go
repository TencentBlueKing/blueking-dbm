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
	"reflect"

	"github.com/pkg/errors"
	"gorm.io/gorm/schema"
	"xorm.io/xorm"

	"dbm-services/common/db-event-consumer/pkg/cst"
)

type XormWriter struct {
	engine *xorm.Engine
}

func NewXormWriter(dsn *InstanceDsn, engine *xorm.Engine) (*XormWriter, error) {
	if engine != nil {
		return &XormWriter{engine: engine}, nil
	}
	if dsn == nil {
		return nil, errors.New("dsn is nil")
	}

	engine, err := GetXormDB(dsn, nil)
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

	return w.engine.Sync(m)

}

func (w *XormWriter) WriteOne(obj interface{}) error {
	var err error
	if omitted, ok := obj.(ModelFieldOmit); ok {
		_, err = w.engine.Omit(omitted.OmitFields()...).Insert(obj)
	} else {
		_, err = w.engine.Insert(obj)
	}
	return err
}

func (w *XormWriter) WriteBatch(table interface{}, ms interface{}) error {
	// xorm table allow &{}, or table name string
	var err error
	tableType := reflect.TypeOf(table).Elem().Name()
	if tableType == cst.NoStrictSchemaModel {
		t, ok := table.(schema.Tabler)
		if !ok {
			return errors.Errorf("FakeModelForNoStrictSchema must implement schema.Tabler")
		}
		if omitted, ok := table.(ModelFieldOmit); ok {
			_, err = w.engine.Table(t.TableName()).Omit(omitted.OmitFields()...).InsertMulti(ms)
		} else {
			_, err = w.engine.Table(t.TableName()).InsertMulti(ms)
		}
	} else {
		if omitted, ok := table.(ModelFieldOmit); ok {
			_, err = w.engine.Table(table).Omit(omitted.OmitFields()...).InsertMulti(ms)
		} else {
			_, err = w.engine.Table(table).InsertMulti(ms)
		}
	}

	return err
}

func (w *XormWriter) XormDB() *xorm.Engine {
	return w.engine
}
