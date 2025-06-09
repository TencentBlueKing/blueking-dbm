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
	var allowCCMouduleInfo dbmapi.DbmEnvData
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
		"status = ? and create_time < date_sub(now(), interval 30 minute) ", model.Unused)
	if len(nocheckBizIds) > 0 {
		qy = qy.Where("dedicated_biz not in (?)", nocheckBizIds)
	}
	if err = qy.Find(&machines).Error; err != nil {
		logger.Error("get unused machines failed %s", err.Error())
		return err
	}
	allowCCMouduleInfo, err = dbmapi.GetDbmEnv()
	if err != nil {
		logger.Error("get dbm env failed %s", err.Error())
		return err
	}
	logger.Info("dba bk bizid %v", allowCCMouduleInfo.DBA_APP_BK_BIZ_ID)
	logger.Info("空闲模块id %v", allowCCMouduleInfo.CC_IDLE_MODULE_ID)
	logger.Info("资源模块信息 %v", allowCCMouduleInfo.CC_MANAGE_TOPO)
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
			BkBizID:   allowCCMouduleInfo.DBA_APP_BK_BIZ_ID,
			BkHostIds: hostgp,
			Page: cc.BKPage{
				Start: 0,
				Limit: len(hostgp),
			},
		})
		if err != nil {
			logger.Error("get host topo relation failed %s", err.Error())
			if ori != nil {
				logger.Error("requesty id:%s,code:%d,messgae:%s", ori.RequestId, ori.Code, ori.Message)
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
			err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_host_id in (?) and  status = ? ",
				hostIds, model.Unused).
				Update("status", model.UsedByOther).Error
			if err != nil {
				logger.Error("update machine status failed %s", err.Error())
				return err
			}
			return nil
		}
		for _, m := range resp.Data {
			if m.BKModuleId == allowCCMouduleInfo.CC_IDLE_MODULE_ID || (m.BKSetId == allowCCMouduleInfo.CC_MANAGE_TOPO.SetId &&
				m.BKModuleId == allowCCMouduleInfo.CC_MANAGE_TOPO.ResourceModuleId) {
				continue
			}
			logger.Info("host %d,set %d  module %d,not allow", m.BKHostId, m.BKSetId, m.BKModuleId)
			err = model.DB.Self.Table(model.TbRpDetailName()).Where(" bk_host_id = ? and  status = ? ",
				m.BKHostId, model.Unused).Updates(map[string]interface{}{"status": model.UsedByOther, "update_time": time.Now()}).
				Error
			if err != nil {
				logger.Error("update machine status failed %s", err.Error())
				return err
			}
		}
	}
	return nil
}
