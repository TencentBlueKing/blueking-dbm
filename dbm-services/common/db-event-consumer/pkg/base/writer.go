// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package base

import (
	"context"
	"database/sql"

	"gorm.io/gorm"
)

type DSWriter interface {
	Type() string
	AutoMigrate(interface{}) error
	WriteBatch(table interface{}, models interface{}) error
	OnDuplicate(objs interface{}) error

	SetWriteMode(mode string)
	GetWriteMode() string
}

type GormMigrator interface {
	GormDB() *gorm.DB
	CloseGormDB() error
}

type DbExec interface {
	ExecContext(ctx context.Context, query string, args ...any) (sql.Result, error)
	Exec(query string, args ...any) (sql.Result, error)
	//Query(query string, args ...any) (*sql.Rows, error)
	//QueryContext(ctx context.Context, query string, args ...any) (*sql.Rows, error)
}
