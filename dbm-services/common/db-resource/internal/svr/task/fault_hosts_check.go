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

	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/go-pubpkg/logger"
)

// FaultHostCheck TODO
func FaultHostCheck() (err error) {
	// 获取空闲机器
	var machines []model.TbRpDetail
	if err = model.DB.Self.Table(model.TbRpDetailName()).
		Where("status = ? ", model.Unused).
		Find(&machines).Error; err != nil {
		logger.Error("get unused machines failed %s", err.Error())
		return err
	}
	if len(machines) == 0 {
		logger.Info("no unused machines found")
		return nil
	}
	for _, mgp := range lo.Chunk(machines, 50) {
		var hosts []dbmapi.CheckFaultHostsParamItem
		for _, m := range mgp {
			hosts = append(hosts, dbmapi.CheckFaultHostsParamItem{
				BkHostID: m.BkHostID,
				IP:       m.IP,
			})
		}
		checkResult, err := dbmapi.CheckFaultHosts(hosts)
		if err != nil {
			logger.Error("check fault hosts failed %s", err.Error())
			continue
		}
		if len(checkResult) == 0 {
			logger.Info("no fault hosts found in this batch")
			continue
		}
		for hostId, item := range checkResult {
			if item.CheckIsOK() {
				continue
			}
			logger.Info("host %s fault info %v", hostId, item)
			err = model.DB.Self.Table(model.TbRpDetailName()).Where(" bk_host_id = ? ",
				hostId).Updates(map[string]interface{}{"status": model.FaultHazard, "update_time": time.Now()}).
				Error
			if err != nil {
				logger.Error("update machine status failed %s", err.Error())
				return err
			}
		}
	}
	return
}
