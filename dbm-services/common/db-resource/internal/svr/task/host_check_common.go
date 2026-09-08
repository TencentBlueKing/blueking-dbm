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
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/go-pubpkg/logger"
)

const (
	hostCheckBatchSize     = 50
	remarkDissolveRecycle  = "巡检发现待裁撤主机，自动转入待回收池"
	remarkFaultToFaultPool = "巡检发现故障主机，自动转入故障池"
)

var (
	fetchSwitchesFn      = dbmapi.GetDissolvedUworkInfo
	checkDissolvedFn     = dbmapi.CheckHostIsDissolved
	checkUworkFn         = dbmapi.CheckHostHasUwork
	resourceDeleteFn     = dbmapi.ResourceDelete
	listUnusedMachinesFn = listUnusedMachines
	markUnusedHostsFn    = markUnusedHosts
)

func listUnusedMachines() ([]model.TbRpDetail, error) {
	var machines []model.TbRpDetail
	err := model.DB.Self.Table(model.TbRpDetailName()).
		Where("status = ?", model.Unused).
		Find(&machines).Error
	return machines, err
}

func markUnusedHosts(hostIds []int, status string) error {
	if len(hostIds) == 0 {
		return nil
	}
	return model.DB.Self.Table(model.TbRpDetailName()).
		Where("bk_host_id in (?) and status = ?", hostIds, model.Unused).
		Updates(map[string]interface{}{"status": status, "update_time": time.Now()}).
		Error
}

func hostIdsOf(machines []model.TbRpDetail) []int {
	ids := make([]int, 0, len(machines))
	for _, m := range machines {
		ids = append(ids, m.BkHostID)
	}
	return ids
}

// filterUnusedHits 只保留本批仍为 Unused 的命中，避免已转故障池的主机再走裁撤
func filterUnusedHits(machines []model.TbRpDetail, hitIds []int) []int {
	unused := make(map[int]struct{}, len(machines))
	for _, m := range machines {
		unused[m.BkHostID] = struct{}{}
	}
	out := make([]int, 0, len(hitIds))
	seen := make(map[int]struct{}, len(hitIds))
	for _, id := range hitIds {
		if _, ok := unused[id]; !ok {
			continue
		}
		if _, dup := seen[id]; dup {
			continue
		}
		seen[id] = struct{}{}
		out = append(out, id)
	}
	return out
}

func buildDeleteHosts(machines []model.TbRpDetail, hostIds []int) []dbmapi.ResourceDeleteHost {
	want := make(map[int]struct{}, len(hostIds))
	for _, id := range hostIds {
		want[id] = struct{}{}
	}
	hosts := make([]dbmapi.ResourceDeleteHost, 0, len(hostIds))
	for _, m := range machines {
		if _, ok := want[m.BkHostID]; !ok {
			continue
		}
		hosts = append(hosts, dbmapi.ResourceDeleteHost{
			BkCloudID: m.BkCloudID,
			IP:        m.IP,
			BkHostID:  m.BkHostID,
		})
	}
	return hosts
}

func markThenMaybeDelete(machines []model.TbRpDetail, hitIds []int, status, event, remark string, doDelete bool) error {
	if err := markUnusedHostsFn(hitIds, status); err != nil {
		logger.Error("update machine status to %s failed %s", status, err.Error())
		return err
	}
	if !doDelete {
		logger.Info("skip resource_delete event=%s, switch is off, hosts=%v", event, hitIds)
		return nil
	}
	if err := resourceDeleteFn(buildDeleteHosts(machines, hitIds), event, remark); err != nil {
		logger.Error("resource delete event=%s failed %s", event, err.Error())
		return err
	}
	return nil
}
