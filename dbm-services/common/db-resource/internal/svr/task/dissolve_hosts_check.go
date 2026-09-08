/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package task

import (
	"fmt"

	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/go-pubpkg/logger"
)

// DissolveHostCheck 巡检资源池空闲主机是否待裁撤。
// HOST_DISSOLVED_SWITCH 控制是否执行整次巡检（扫描、标记 Dissolved、转入待回收池）。
func DissolveHostCheck() (err error) {
	enabled, err := dissolveInspectEnabled()
	if err != nil {
		return err
	}
	if !enabled {
		return nil
	}

	machines, err := listUnusedMachinesFn()
	if err != nil {
		logger.Error("get unused machines failed %s", err.Error())
		return err
	}
	if len(machines) == 0 {
		logger.Info("no unused machines found for dissolve check")
		return nil
	}

	var failedBatches int
	var lastErr error
	for _, mgp := range lo.Chunk(machines, hostCheckBatchSize) {
		if batchErr := processDissolveBatch(mgp); batchErr != nil {
			failedBatches++
			lastErr = batchErr
		}
	}
	if failedBatches > 0 {
		return fmt.Errorf("dissolve check failed for %d batches, last: %w", failedBatches, lastErr)
	}
	return nil
}

func dissolveInspectEnabled() (bool, error) {
	switches, err := fetchSwitchesFn()
	if err != nil {
		logger.Error("get dissolved uwork info failed %s", err.Error())
		return false, err
	}
	if !switches.HostDissolvedSwitch {
		logger.Info("HOST_DISSOLVED_SWITCH is off, skip dissolve inspect")
		return false, nil
	}
	return true, nil
}

func processDissolveBatch(mgp []model.TbRpDetail) error {
	dissolvedHostIds, checkErr := checkDissolvedFn(hostIdsOf(mgp))
	if checkErr != nil {
		logger.Error("check dissolve hosts failed %s", checkErr.Error())
		return checkErr
	}
	hitIds := filterUnusedHits(mgp, dissolvedHostIds)
	if len(hitIds) == 0 {
		logger.Info("no dissolved hosts found in this batch")
		return nil
	}
	logger.Info("found dissolved hosts %v", hitIds)
	return markThenMaybeDelete(mgp, hitIds, model.Dissolved, dbmapi.EventToRecycle, remarkDissolveRecycle, true)
}
