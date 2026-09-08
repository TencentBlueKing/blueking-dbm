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

// FaultHostCheck 巡检资源池空闲主机是否有未关闭 uwork，命中则标记 FaultHazard。
// HOST_TO_FAULT_SWITCH 只控制是否再调 resource_delete 转入故障池。
func FaultHostCheck() (err error) {
	machines, err := listUnusedMachinesFn()
	if err != nil {
		logger.Error("get unused machines failed %s", err.Error())
		return err
	}
	if len(machines) == 0 {
		logger.Info("no unused machines found")
		return nil
	}

	doDelete, switchErr := faultDeleteEnabled()
	var failedBatches int
	var lastErr error
	for _, mgp := range lo.Chunk(machines, hostCheckBatchSize) {
		if batchErr := processFaultBatch(mgp, doDelete); batchErr != nil {
			failedBatches++
			lastErr = batchErr
		}
	}
	if failedBatches > 0 {
		return fmt.Errorf("fault check failed for %d batches, last: %w", failedBatches, lastErr)
	}
	return switchErr
}

func faultDeleteEnabled() (bool, error) {
	switches, err := fetchSwitchesFn()
	if err != nil {
		logger.Error("get dissolved uwork info failed %s", err.Error())
		return false, err
	}
	if !switches.HostToFaultSwitch {
		logger.Info("HOST_TO_FAULT_SWITCH is off, skip resource_delete")
		return false, nil
	}
	return true, nil
}

func processFaultBatch(mgp []model.TbRpDetail, doDelete bool) error {
	uworkHosts, checkErr := checkUworkFn(hostIdsOf(mgp))
	if checkErr != nil {
		logger.Error("check uwork hosts failed %s", checkErr.Error())
		return checkErr
	}
	hitIds := make([]int, 0, len(uworkHosts))
	for _, h := range uworkHosts {
		hitIds = append(hitIds, h.BkHostID)
	}
	hitIds = filterUnusedHits(mgp, hitIds)
	if len(hitIds) == 0 {
		logger.Info("no fault hosts found in this batch")
		return nil
	}
	logger.Info("found fault hosts %v", hitIds)
	return markThenMaybeDelete(mgp, hitIds, model.FaultHazard, dbmapi.EventToFault, remarkFaultToFaultPool, doDelete)
}
