/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dtsutil

import (
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/require"
)

func TestResolveTablesListLockTables(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	tables, err := ResolveTablesList(db, nil, []TableItem{{Schema: "app", Table: "t1"}})
	require.NoError(t, err)
	require.Equal(t, []LockedTable{{Schema: "app", Table: "t1"}}, tables)
	require.NoError(t, mock.ExpectationsWereMet())
}

func TestResolveTablesListRejectEmptyLockSchema(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()
	_, err = ResolveTablesList(db, nil, []TableItem{{Schema: "", Table: "t1"}})
	require.Error(t, err)
	require.NoError(t, mock.ExpectationsWereMet())
}

func TestVerifyBaseTablesExist(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	mock.ExpectQuery("SELECT 1").
		WithArgs("app", "t1").
		WillReturnRows(sqlmock.NewRows([]string{"1"}).AddRow(1))

	require.NoError(t, VerifyBaseTablesExist(db, []LockedTable{{Schema: "app", Table: "t1"}}))
	require.NoError(t, mock.ExpectationsWereMet())
}

func TestVerifyBaseTablesExistMissing(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	mock.ExpectQuery("SELECT 1").
		WithArgs("app", "missing").
		WillReturnRows(sqlmock.NewRows([]string{"1"}))

	err = VerifyBaseTablesExist(db, []LockedTable{{Schema: "app", Table: "missing"}})
	require.Error(t, err)
	require.Contains(t, err.Error(), "表不存在")
	require.NoError(t, mock.ExpectationsWereMet())
}

func TestResolveTablesForPrecheck(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	mock.ExpectQuery("SELECT 1").
		WithArgs("app", "t1").
		WillReturnRows(sqlmock.NewRows([]string{"1"}).AddRow(1))

	tables, err := ResolveTablesForPrecheck(db, nil, []TableItem{{Schema: "app", Table: "t1"}})
	require.NoError(t, err)
	require.Len(t, tables, 1)
	require.NoError(t, mock.ExpectationsWereMet())
}
