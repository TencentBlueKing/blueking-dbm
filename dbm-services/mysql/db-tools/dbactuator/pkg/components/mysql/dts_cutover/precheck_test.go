/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dts_cutover

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/stretchr/testify/require"
)

func TestValidateTaskStatusFetchable(t *testing.T) {
	require.Error(t, validateTaskStatusFetchable(nil))
	require.Error(t, validateTaskStatusFetchable(&TaskStatusListResponse{}))
	require.NoError(t, validateTaskStatusFetchable(&TaskStatusListResponse{
		Data: []TaskStatusItem{{Name: "t", Stage: "Stopped"}},
	}))
}

func TestValidateTaskStatusFetchableIgnoresBlockingDDLAndStage(t *testing.T) {
	// AE3 / AE5：非运行态 + blocking_ddls 仍可通过「任务可查」门禁
	err := validateTaskStatusFetchable(&TaskStatusListResponse{
		Data: []TaskStatusItem{{
			Name:  "t",
			Stage: "Paused",
			SyncStatus: &SyncStatus{
				BlockingDDLs: []string{"ALTER TABLE t"},
			},
		}},
	})
	require.NoError(t, err)
}

func TestResolveTablesListLockTables(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()

	tables, err := resolveTablesList(db, nil, []TableItem{{Schema: "app", Table: "t1"}})
	require.NoError(t, err)
	require.Equal(t, []LockedTable{{Schema: "app", Table: "t1"}}, tables)
	require.NoError(t, mock.ExpectationsWereMet())
}

func TestResolveTablesListRejectEmptyLockSchema(t *testing.T) {
	db, mock, err := sqlmock.New()
	require.NoError(t, err)
	defer db.Close()
	_, err = resolveTablesList(db, nil, []TableItem{{Schema: "", Table: "t1"}})
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

func TestPreCheckChecksumGate(t *testing.T) {
	c := &Comp{Params: &Params{
		DtsMasterAddr: "127.0.0.2:18301",
		TaskName:      "task-a",
		SourceEndpoints: []SourceEndpoint{{
			Host: "127.0.0.10", Port: 20000, User: "u", Password: "p",
		}},
		SyncScope:      &SyncScope{DoDBs: []string{"app"}},
		ChecksumPassed: false,
		SkipChecksum:   false,
	}}
	err := c.PreCheck()
	require.Error(t, err)
	require.Contains(t, err.Error(), "checksum")
}

func TestPreCheckSourceConnectFailFast(t *testing.T) {
	c := &Comp{Params: &Params{
		DtsMasterAddr: "127.0.0.2:18301",
		TaskName:      "task-a",
		SourceEndpoints: []SourceEndpoint{
			{Host: "127.0.0.1", Port: 1, User: "u", Password: "p", SourceName: "src1"},
			{Host: "127.0.0.1", Port: 2, User: "u", Password: "p", SourceName: "src2"},
		},
		SyncScope:      &SyncScope{DoDBs: []string{"app"}},
		ChecksumPassed: true,
	}}
	err := c.PreCheck()
	require.Error(t, err)
	require.Contains(t, err.Error(), "预检连接源端")
	require.Contains(t, err.Error(), "src1")
	require.False(t, strings.Contains(err.Error(), "src2"), "fail-fast 不应继续到第二源")
}

func TestFetchTaskStatusAndValidateOK(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.Contains(t, r.URL.Path, "/api/v1/tasks/")
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"total":1,"data":[{"name":"task-a","stage":"Paused","sync_status":{"blocking_ddls":["x"],"seconds_behind_master":0}}]}`))
	}))
	defer srv.Close()

	addr := strings.TrimPrefix(srv.URL, "http://")
	resp, err := FetchTaskStatus(addr, "task-a", 5)
	require.NoError(t, err)
	require.NoError(t, validateTaskStatusFetchable(resp))
	require.Equal(t, "Paused", resp.Data[0].Stage)
	require.NotEmpty(t, resp.Data[0].SyncStatus.BlockingDDLs)
}

func TestFetchTaskStatusEmptyData(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"total":0,"data":[]}`))
	}))
	defer srv.Close()
	addr := strings.TrimPrefix(srv.URL, "http://")
	resp, err := FetchTaskStatus(addr, "missing", 5)
	require.NoError(t, err)
	require.Error(t, validateTaskStatusFetchable(resp))
}
