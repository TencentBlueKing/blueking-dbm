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
	"errors"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func caughtUpItem(source string, stage TaskStage, errMsg string) TaskStatusItem {
	return TaskStatusItem{
		SourceName: source,
		Stage:      stage,
		ErrorMsg:   errMsg,
		SyncStatus: &SyncStatus{
			SecondsBehindMaster: 0,
			MasterBinlog:        "(binlog.000001, 200)",
			SyncerBinlog:        "(binlog.000001, 100)",
		},
	}
}

func behindItem(source string, stage TaskStage) TaskStatusItem {
	item := caughtUpItem(source, stage, "")
	item.SyncStatus.SyncerBinlog = "(binlog.000001, 90)"
	return item
}

func lockSnap() map[string]BinlogCoord {
	snap, ok := ParseBinlogCoord("(binlog.000001, 100)")
	if !ok {
		panic("lock snap")
	}
	return map[string]BinlogCoord{"src1": snap}
}

func TestPollUntilCaughtUpAbortsOnErrorMsgWithoutFurtherPolls(t *testing.T) {
	snaps := lockSnap()
	calls := 0
	_, err := pollUntilCaughtUp(func() ([]TaskStatusItem, error) {
		calls++
		return []TaskStatusItem{caughtUpItem("src1", TaskStagePaused, "syncer boom")}, nil
	}, snaps, 3, 300, func() { t.Fatal("报错后不应再 sleep 轮询") })
	require.Equal(t, 1, calls)
	require.Error(t, err)
	require.Contains(t, err.Error(), "不执行 stop")
	require.Contains(t, err.Error(), "任务错误")
	require.Contains(t, err.Error(), "syncer boom")
}

func TestPollUntilCaughtUpAbortsOnInvalidStage(t *testing.T) {
	snaps := lockSnap()
	for _, errMsg := range []string{"", "bad stage"} {
		errMsg := errMsg
		calls := 0
		_, err := pollUntilCaughtUp(func() ([]TaskStatusItem, error) {
			calls++
			return []TaskStatusItem{caughtUpItem("src1", TaskStageInvalidStage, errMsg)}, nil
		}, snaps, 3, 300, func() { t.Fatal("InvalidStage 不应继续轮询") })
		require.Equal(t, 1, calls)
		require.Error(t, err)
		require.Contains(t, err.Error(), "不执行 stop")
		if errMsg != "" {
			require.Contains(t, err.Error(), errMsg)
			continue
		}
		require.Contains(t, err.Error(), string(TaskStageInvalidStage))
	}
}

func TestPollUntilCaughtUpRunningWithErrorMsgStillPasses(t *testing.T) {
	snaps := lockSnap()
	calls := 0
	_, err := pollUntilCaughtUp(func() ([]TaskStatusItem, error) {
		calls++
		return []TaskStatusItem{caughtUpItem("src1", TaskStageRunning, "stale")}, nil
	}, snaps, 3, 300, func() {})
	require.NoError(t, err)
	require.Equal(t, 3, calls)
}

func TestPollUntilCaughtUpKeepsPollingWhenNotCaughtUp(t *testing.T) {
	snaps := lockSnap()
	calls := 0
	_, err := pollUntilCaughtUp(func() ([]TaskStatusItem, error) {
		calls++
		return []TaskStatusItem{behindItem("src1", TaskStageRunning)}, nil
	}, snaps, 3, 4, func() {})
	require.Equal(t, 4, calls)
	require.Error(t, err)
	require.Contains(t, err.Error(), "持锁复核超时")
	require.NotContains(t, err.Error(), "任务报错")
}

func TestPollUntilCaughtUpKeepsPollingPausedAndBlockingDDL(t *testing.T) {
	snaps := lockSnap()
	for _, item := range []TaskStatusItem{
		behindItem("src1", TaskStagePaused),
		behindItem("src1", TaskStageStopped),
		func() TaskStatusItem {
			item := behindItem("src1", TaskStageRunning)
			item.SyncStatus.BlockingDDLs = []string{"ALTER TABLE t"}
			return item
		}(),
	} {
		calls := 0
		_, err := pollUntilCaughtUp(func() ([]TaskStatusItem, error) {
			calls++
			return []TaskStatusItem{item}, nil
		}, snaps, 3, 2, func() {})
		require.Equal(t, 2, calls)
		require.Contains(t, err.Error(), "持锁复核超时")
	}
}

func TestPollUntilCaughtUpPassesAfterConsecutiveRecheck(t *testing.T) {
	snaps := lockSnap()
	calls := 0
	items, err := pollUntilCaughtUp(func() ([]TaskStatusItem, error) {
		calls++
		return []TaskStatusItem{caughtUpItem("src1", TaskStageRunning, "")}, nil
	}, snaps, 3, 300, func() {})
	require.NoError(t, err)
	require.Equal(t, 3, calls)
	require.Equal(t, "src1", items[0].SourceName)
}

func TestPollUntilCaughtUpPausedButCaughtUpStillPasses(t *testing.T) {
	snaps := lockSnap()
	calls := 0
	_, err := pollUntilCaughtUp(func() ([]TaskStatusItem, error) {
		calls++
		return []TaskStatusItem{caughtUpItem("src1", TaskStagePaused, "")}, nil
	}, snaps, 3, 300, func() {})
	require.NoError(t, err)
	require.Equal(t, 3, calls)
}

func TestPollUntilCaughtUpAbortsWhenLaterSourceErrors(t *testing.T) {
	snap1, _ := ParseBinlogCoord("(binlog.000001, 100)")
	snap2, _ := ParseBinlogCoord("(binlog.000001, 50)")
	snaps := map[string]BinlogCoord{"src1": snap1, "src2": snap2}
	src2 := caughtUpItem("src2", TaskStagePaused, "syncer boom")
	src2.SyncStatus.SyncerBinlog = "(binlog.000001, 50)"
	calls := 0
	_, err := pollUntilCaughtUp(func() ([]TaskStatusItem, error) {
		calls++
		return []TaskStatusItem{
			caughtUpItem("src1", TaskStageRunning, ""),
			src2,
		}, nil
	}, snaps, 3, 300, func() { t.Fatal("第二源报错后不应再轮询") })
	require.Equal(t, 1, calls)
	require.Error(t, err)
	require.Contains(t, err.Error(), "src2")
}

func TestPollUntilCaughtUpFetchErrorExitsImmediately(t *testing.T) {
	calls := 0
	_, err := pollUntilCaughtUp(func() ([]TaskStatusItem, error) {
		calls++
		return nil, errors.New("dial timeout")
	}, lockSnap(), 3, 300, func() { t.Fatal("查询失败不应 sleep 后重试") })
	require.Equal(t, 1, calls)
	require.Contains(t, err.Error(), "持锁复核追平失败")
	require.Contains(t, err.Error(), "dial timeout")
}

func TestDefaultCatchupBudget(t *testing.T) {
	require.Equal(t, 30, defaultPrecheckPollMax)
	require.Equal(t, time.Second, precheckPollInterval)
	require.Equal(t, 60, defaultCatchupPollMax)
	require.Equal(t, 500*time.Millisecond, catchupPollInterval)
}

func laggingItem(source string) TaskStatusItem {
	item := caughtUpItem(source, TaskStageRunning, "")
	item.SyncStatus.SecondsBehindMaster = 5
	return item
}

func TestPollReadyBeforeLockWaitsUntilSbmZero(t *testing.T) {
	calls := 0
	sleeps := 0
	err := pollReadyBeforeLock(func() ([]TaskStatusItem, error) {
		calls++
		if calls == 1 {
			return []TaskStatusItem{laggingItem("src1")}, nil
		}
		return []TaskStatusItem{caughtUpItem("src1", TaskStageRunning, "")}, nil
	}, 30, func() { sleeps++ })
	require.NoError(t, err)
	require.Equal(t, 2, calls)
	require.Equal(t, 1, sleeps)
}

func TestPollReadyBeforeLockTimesOutWithoutLockingMessage(t *testing.T) {
	calls := 0
	err := pollReadyBeforeLock(func() ([]TaskStatusItem, error) {
		calls++
		return []TaskStatusItem{laggingItem("src1")}, nil
	}, 3, func() {})
	require.Equal(t, 3, calls)
	require.Contains(t, err.Error(), "预检追平超时（未加锁）")
	require.Contains(t, err.Error(), "sbm=5")
}

func TestPollReadyBeforeLockAbortsOnTaskError(t *testing.T) {
	calls := 0
	err := pollReadyBeforeLock(func() ([]TaskStatusItem, error) {
		calls++
		return []TaskStatusItem{caughtUpItem("src1", TaskStagePaused, "syncer boom")}, nil
	}, 30, func() { t.Fatal("报错后不应再 sleep") })
	require.Equal(t, 1, calls)
	require.Contains(t, err.Error(), "未加锁")
	require.Contains(t, err.Error(), "syncer boom")
}

func TestPollReadyBeforeLockAbortsWhenNotRunning(t *testing.T) {
	calls := 0
	err := pollReadyBeforeLock(func() ([]TaskStatusItem, error) {
		calls++
		return []TaskStatusItem{caughtUpItem("src1", TaskStageStopped, "")}, nil
	}, 30, func() { t.Fatal("非 Running 不应继续轮询") })
	require.Equal(t, 1, calls)
	require.Contains(t, err.Error(), "预检任务不在运行中")
}
