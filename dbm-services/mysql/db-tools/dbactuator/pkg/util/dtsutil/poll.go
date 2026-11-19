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
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
)

type pollAction int

const (
	pollPass pollAction = iota
	pollRetry
	pollAbort
)

func decideCatchupPoll(items []TaskStatusItem, snapshots map[string]BinlogCoord) (pollAction, error) {
	if err := TaskReportError(items); err != nil {
		return pollAbort, err
	}
	if err := CheckSnapshotCatchup(items, snapshots); err != nil {
		return pollRetry, err
	}
	return pollPass, nil
}

func decideReadyBeforeLock(items []TaskStatusItem) (pollAction, error) {
	if err := TaskReportError(items); err != nil {
		return pollAbort, err
	}
	if err := ValidateTaskRunning(&TaskStatusListResponse{Data: items}); err != nil {
		return pollAbort, err
	}
	if err := SourcesQuietEnoughToLock(items); err != nil {
		return pollRetry, err
	}
	return pollPass, nil
}

// PollReadyBeforeLock 在加锁之前等到各源 Running 且 SBM==0；报错或非 Running 立刻失败。
func PollReadyBeforeLock(
	fetch func() ([]TaskStatusItem, error),
	pollMax int,
	sleep func(),
) error {
	if pollMax < 1 {
		pollMax = 1
	}
	var lastErr error
	for attempt := 0; attempt < pollMax; attempt++ {
		if attempt > 0 && sleep != nil {
			sleep()
		}
		items, ferr := fetch()
		if ferr != nil {
			return fmt.Errorf("查询任务状态失败: %w", ferr)
		}
		action, cerr := decideReadyBeforeLock(items)
		switch action {
		case pollAbort:
			return fmt.Errorf("任务状态检查失败: %w", cerr)
		case pollRetry:
			lastErr = cerr
			logger.Warn("就绪检查未通过 attempt=%d/%d: %s", attempt+1, pollMax, cerr.Error())
			continue
		default:
			logger.Info("就绪检查通过 attempt=%d/%d", attempt+1, pollMax)
			return nil
		}
	}
	if lastErr == nil {
		lastErr = fmt.Errorf("未观察到就绪状态")
	}
	return fmt.Errorf("等待就绪超时: %w", lastErr)
}

// PollUntilCaughtUp 持锁后按加锁快照复核追平，连续通过 recheck 次才返回本轮 status。
func PollUntilCaughtUp(
	fetch func() ([]TaskStatusItem, error),
	snapshots map[string]BinlogCoord,
	recheck int,
	pollMax int,
	sleep func(),
) ([]TaskStatusItem, error) {
	if recheck < 1 {
		recheck = 1
	}
	if pollMax < 1 {
		pollMax = 1
	}
	var statusItems []TaskStatusItem
	consecutive := 0
	var lastCatchupErr error
	for attempt := 0; attempt < pollMax; attempt++ {
		if attempt > 0 && sleep != nil {
			sleep()
		}
		items, ferr := fetch()
		if ferr != nil {
			return nil, fmt.Errorf("查询任务状态失败: %w", ferr)
		}
		statusItems = items
		action, cerr := decideCatchupPoll(items, snapshots)
		switch action {
		case pollAbort:
			return nil, fmt.Errorf("任务状态检查失败: %w", cerr)
		case pollRetry:
			consecutive = 0
			lastCatchupErr = cerr
			logger.Warn("追平检查未通过 attempt=%d/%d: %s", attempt+1, pollMax, cerr.Error())
			continue
		default:
			consecutive++
			lastCatchupErr = nil
			logger.Info("追平检查通过 (%d/%d) attempt=%d/%d", consecutive, recheck, attempt+1, pollMax)
			if consecutive >= recheck {
				return statusItems, nil
			}
		}
	}
	if lastCatchupErr == nil {
		lastCatchupErr = fmt.Errorf("连续通过次数不足: got=%d want=%d", consecutive, recheck)
	}
	return nil, fmt.Errorf("追平超时: %w", lastCatchupErr)
}
