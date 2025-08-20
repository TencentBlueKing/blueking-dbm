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
	"strconv"
	"strings"
	"time"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/dbmapi"

	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// InspectCheckResource inspection resource
// nolint
func InspectCheckResource() (err error) {
	//  获取空闲机器
	var machines []model.TbRpDetail
	var allowCCModuleInfo dbmapi.DbmEnvData
	// 获取不需要要检查的业务
	nocheckBizIds := []int{}
	logger.Info("apply not inspection bizids %s", config.AppConfig.NotInspectionBizids)
	if lo.IsNotEmpty(config.AppConfig.NotInspectionBizids) {
		for _, v := range strings.Split(config.AppConfig.NotInspectionBizids, ",") {
			bizid, errx := strconv.Atoi(v)
			if errx != nil {
				logger.Error("strconv.Atoi failed %s", errx.Error())
				continue
			}
			nocheckBizIds = append(nocheckBizIds, bizid)
		}
	}
	qy := model.DB.Self.Table(model.TbRpDetailName()).Where(
		"status = ? and create_time < date_sub(now(), interval 10 minute) ", model.Unused)
	if len(nocheckBizIds) > 0 {
		qy = qy.Where("dedicated_biz not in (?)", nocheckBizIds)
	}
	if err = qy.Find(&machines).Error; err != nil {
		logger.Error("get unused machines failed %s", err.Error())
		return err
	}
	allowCCModuleInfo, err = dbmapi.GetDbmEnv()
	if err != nil {
		logger.Error("get dbm env failed %s", err.Error())
		return err
	}
	logger.Info("dba bk biz id %v", allowCCModuleInfo.RESOURCE_INDEPENDENT_BIZ)
	logger.Info("空闲模块id %v", allowCCModuleInfo.CC_IDLE_MODULE_ID)
	logger.Info("资源模块信息 %v", allowCCModuleInfo.CC_MANAGE_TOPO)
	// hostIdMap := make(map[int][]int)
	// for _, machine := range machines {
	// 	hostIdMap[machine.BkBizId] = append(hostIdMap[machine.BkBizId], machine.BkHostID)
	// }
	hostIds := []int{}
	for _, machine := range machines {
		hostIds = append(hostIds, machine.BkHostID)
	}
	for _, hostgp := range cmutil.SplitGroup(hostIds, 200) {
		resp, ori, err := cc.NewFindHostTopoRelation(bk.BkCmdbClient).Query(&cc.FindHostTopoRelationParam{
			BkBizID:   allowCCModuleInfo.RESOURCE_INDEPENDENT_BIZ,
			BkHostIds: hostgp,
			Page: cc.BKPage{
				Start: 0,
				Limit: len(hostgp),
			},
		})
		if err != nil {
			logger.Error("get host topo relation failed %s", err.Error())
			if ori != nil {
				logger.Error("request id:%s,code:%d,message:%s", ori.RequestId, ori.Code, ori.Message)
			}
			continue
			// return err
		}
		logger.Info("get host topo relation success %v", resp.Data)
		// filter all exist bkhostId
		bkhostIds := []int{}
		for _, m := range resp.Data {
			bkhostIds = append(bkhostIds, m.BKHostId)
		}
		if len(bkhostIds) == 0 {
			logger.Info("没差查询到host ids:[%v]任何模块信息", hostgp)

			// 先查询要更新的机器信息，用于记录状态变更日志
			var machineDetails []model.TbRpDetail
			err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_host_id in (?) and  status = ? ",
				hostIds, model.Unused).Find(&machineDetails).Error
			if err != nil {
				logger.Error("query machine details failed %s", err.Error())
				return err
			}

			// 更新状态
			err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_host_id in (?) and  status = ? ",
				hostIds, model.Unused).
				Update("status", model.UsedByOther).Error
			if err != nil {
				logger.Error("update machine status failed %s", err.Error())
				return err
			}

			// 记录状态变更日志
			for _, machine := range machineDetails {
				requestID := ori.RequestId
				batchSize := len(hostgp)
				inspectionType := "cc_topo_relation_check"
				context := &model.StatusChangeContext{
					// 主机业务信息
					BKBizID:      &machine.BkBizId,
					DedicatedBiz: &machine.DedicatedBiz,

					// 资源信息
					SubZone:     &machine.SubZone,
					SubZoneID:   &machine.SubZoneID,
					City:        &machine.City,
					CityID:      &machine.CityID,
					DeviceClass: &machine.DeviceClass,

					// 允许的模块信息
					AllowedModules: []int{allowCCModuleInfo.CC_MANAGE_TOPO.ResourceModuleId},

					// 其他信息
					RequestID:      &requestID,
					BatchSize:      &batchSize,
					InspectionType: &inspectionType,
				}
				model.LogStatusChange(
					machine.BkHostID,
					machine.IP,
					machine.BkCloudID,
					model.Unused,
					model.UsedByOther,
					model.ReasonHostNotFoundInCC,
					fmt.Sprintf("在CC中查询不到主机ID[%v]的模块信息，业务ID[%d]，园区[%s]", hostgp, machine.BkBizId, machine.SubZone),
					context,
					"system",
				)
			}
			return nil
		}
		for _, m := range resp.Data {
			if m.BKModuleId == allowCCModuleInfo.CC_MANAGE_TOPO.ResourceModuleId {
				continue
			}
			logger.Info("host %d,set %d  module %d,not allow", m.BKHostId, m.BKSetId, m.BKModuleId)

			// 先查询机器详细信息，用于记录状态变更日志
			var machineDetail model.TbRpDetail
			err = model.DB.Self.Table(model.TbRpDetailName()).Where(" bk_host_id = ? and  status = ? ",
				m.BKHostId, model.Unused).First(&machineDetail).Error
			if err != nil {
				logger.Error("query machine detail failed %s", err.Error())
				return err
			}

			// 更新状态
			err = model.DB.Self.Table(model.TbRpDetailName()).Where(" bk_host_id = ? and  status = ? ",
				m.BKHostId, model.Unused).Updates(map[string]interface{}{"status": model.UsedByOther, "update_time": time.Now()}).
				Error
			if err != nil {
				logger.Error("update machine status failed %s", err.Error())
				return err
			}

			// 记录状态变更日志
			requestID := ori.RequestId
			inspectionType := "cc_module_validation"
			context := &model.StatusChangeContext{
				// 主机业务信息
				BKBizID:      &machineDetail.BkBizId,
				DedicatedBiz: &machineDetail.DedicatedBiz,

				// CC拓扑信息
				BKSetID:        &m.BKSetId,
				BKModuleID:     &m.BKModuleId,
				AllowedModules: []int{allowCCModuleInfo.CC_MANAGE_TOPO.ResourceModuleId},

				// 资源信息
				SubZone:     &machineDetail.SubZone,
				SubZoneID:   &machineDetail.SubZoneID,
				City:        &machineDetail.City,
				CityID:      &machineDetail.CityID,
				DeviceClass: &machineDetail.DeviceClass,

				// 其他信息
				RequestID:      &requestID,
				InspectionType: &inspectionType,
			}
			model.LogStatusChange(
				machineDetail.BkHostID,
				machineDetail.IP,
				machineDetail.BkCloudID,
				model.Unused,
				model.UsedByOther,
				model.ReasonCCModuleNotAllow,
				fmt.Sprintf("主机所在模块ID[%d]不在允许的资源模块[%d]范围内，当前业务ID[%d]，集合ID[%d]，园区[%s]",
					m.BKModuleId, allowCCModuleInfo.CC_MANAGE_TOPO.ResourceModuleId, machineDetail.BkBizId, m.BKSetId, machineDetail.SubZone),
				context,
				"system",
			)
		}
	}
	return nil
}
