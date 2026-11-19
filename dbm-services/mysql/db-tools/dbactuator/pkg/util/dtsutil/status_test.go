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
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestValidateTaskRunning(t *testing.T) {
	require.Error(t, ValidateTaskRunning(nil))
	require.Error(t, ValidateTaskRunning(&TaskStatusListResponse{}))
	require.NoError(t, ValidateTaskRunning(&TaskStatusListResponse{
		Data: []TaskStatusItem{{Name: "t", Stage: TaskStageRunning}},
	}))
	err := ValidateTaskRunning(&TaskStatusListResponse{
		Data: []TaskStatusItem{{Name: "t", SourceName: "src1", Stage: TaskStageStopped}},
	})
	require.Error(t, err)
	require.Contains(t, err.Error(), "src1")
	require.Contains(t, err.Error(), string(TaskStageStopped))
}

func TestValidateTaskRunningRejectsPausedWithError(t *testing.T) {
	err := ValidateTaskRunning(&TaskStatusListResponse{
		Data: []TaskStatusItem{{
			SourceName: "src1",
			Stage:      TaskStagePaused,
			ErrorMsg:   "syncer boom",
			SyncStatus: &SyncStatus{BlockingDDLs: []string{"ALTER TABLE t"}},
		}},
	})
	require.Error(t, err)
	require.Contains(t, err.Error(), "syncer boom")
}

func TestValidateTaskRunningAllowsBlockingDDLWhileRunning(t *testing.T) {
	err := ValidateTaskRunning(&TaskStatusListResponse{
		Data: []TaskStatusItem{{
			Name:  "t",
			Stage: TaskStageRunning,
			SyncStatus: &SyncStatus{
				BlockingDDLs: []string{"ALTER TABLE t"},
			},
		}},
	})
	require.NoError(t, err)
}

func TestFetchTaskStatusAndValidateOK(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.Contains(t, r.URL.Path, "/api/v1/tasks/")
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"total":1,"data":[{"name":"task-a","stage":"Running","sync_status":{"blocking_ddls":["x"],"seconds_behind_master":0}}]}`))
	}))
	defer srv.Close()

	addr := strings.TrimPrefix(srv.URL, "http://")
	resp, err := FetchTaskStatus(addr, "task-a", 5)
	require.NoError(t, err)
	require.NoError(t, ValidateTaskRunning(resp))
	require.Equal(t, TaskStageRunning, resp.Data[0].Stage)
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
	require.Error(t, ValidateTaskRunning(resp))
}

func TestBuildLockMasterSnapshots(t *testing.T) {
	snaps, err := BuildLockMasterSnapshots([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{MasterBinlog: "(binlog.000001, 100)"},
		},
	})
	require.NoError(t, err)
	require.Equal(t, "binlog.000001", snaps["src1"].File)
	require.Equal(t, int64(100), snaps["src1"].Position)
}

func TestCheckSnapshotCatchupBlockingDDL(t *testing.T) {
	snap, _ := ParseBinlogCoord("(binlog.000001, 100)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
				BlockingDDLs:        []string{"ALTER TABLE t"},
			},
		},
	}, map[string]BinlogCoord{"src1": snap})
	require.Error(t, err)
	require.Contains(t, err.Error(), "blocking_ddls")
}

func TestCheckSnapshotCatchupLiveMasterAheadOK(t *testing.T) {
	// 加锁快照=100；实时 master 因未迁移表前进到 200；syncer 已追到 100 → 通过
	snap, _ := ParseBinlogCoord("(binlog.000001, 100)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap})
	require.NoError(t, err)
}

func TestCheckSnapshotCatchupSyncerBehindRejected(t *testing.T) {
	snap, _ := ParseBinlogCoord("(binlog.000001, 100)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 90)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap})
	require.Error(t, err)
	require.Contains(t, err.Error(), "未追上加锁快照")
}

func TestCheckSnapshotCatchupSBMRejected(t *testing.T) {
	snap, _ := ParseBinlogCoord("(binlog.000001, 100)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 1,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap})
	require.Error(t, err)
}

func TestCheckSnapshotCatchupMultiSourceOneBehind(t *testing.T) {
	snap1, _ := ParseBinlogCoord("(binlog.000001, 100)")
	snap2, _ := ParseBinlogCoord("(binlog.000001, 50)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
		{
			SourceName: "src2",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 80)",
				SyncerBinlog:        "(binlog.000001, 40)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap1, "src2": snap2})
	require.Error(t, err)
	require.Contains(t, err.Error(), "src2")
}

func TestCheckSnapshotCatchupMissingSnapshot(t *testing.T) {
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 100)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
	}, map[string]BinlogCoord{})
	require.Error(t, err)
}

func TestCheckSnapshotCatchupMissingStatusSource(t *testing.T) {
	// snapshots 有两源，本轮 status 只回一源且已追平 → 必须失败（禁止子集假成功）
	snap1, _ := ParseBinlogCoord("(binlog.000001, 100)")
	snap2, _ := ParseBinlogCoord("(binlog.000001, 50)")
	err := CheckSnapshotCatchup([]TaskStatusItem{
		{
			SourceName: "src1",
			SyncStatus: &SyncStatus{
				SecondsBehindMaster: 0,
				MasterBinlog:        "(binlog.000001, 200)",
				SyncerBinlog:        "(binlog.000001, 100)",
			},
		},
	}, map[string]BinlogCoord{"src1": snap1, "src2": snap2})
	require.Error(t, err)
	require.Contains(t, err.Error(), "src2")
	require.Contains(t, err.Error(), "未返回该源")
}
