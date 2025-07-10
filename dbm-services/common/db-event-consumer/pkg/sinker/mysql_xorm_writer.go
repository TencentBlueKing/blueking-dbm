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
	"xorm.io/xorm"
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

// CustomWrite fake implementation
func (w *XormWriter) CustomWrite(m interface{}, f func(i interface{}, db *gorm.DB) error) error {
	if f != nil {
		return f(m, &gorm.DB{})
	}
	_, err := w.engine.Table(m).InsertMulti(m)
	return err
}

func (w *XormWriter) CustomWrite2(m interface{}, f func(i interface{}, engine *xorm.Engine) error) error {
	// func(interface{}, sinker.DSWriter)
	if f != nil {
		return f(m, w.engine)
	}
	_, err := w.engine.Table(m).InsertMulti(m)
	return err
	//return nil
}

func (w *XormWriter) WriteBatch(table interface{}, ms interface{}) error {
	var err error
	if omitted, ok := table.(ModelFieldOmit); ok {
		_, err = w.engine.Omit(omitted.OmitFields()...).Table(table).InsertMulti(ms)
	} else {
		_, err = w.engine.Table(table).InsertMulti(ms)
	}
	return err
}

func (w *XormWriter) XormDB() *xorm.Engine {
	return w.engine
}
