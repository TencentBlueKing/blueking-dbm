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
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/meta"
	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// InspectCheckResource TODO
func InspectCheckResource() (err error) {
	//  获取空闲机器
	var machines []model.TbRpDetail
	var allowCCMouduleInfo meta.DbmEnvData
	err = model.DB.Self.Table(model.TbRpDetailName()).Find(&machines, "status = ?", model.Unused).Error
	if err != nil {
		logger.Error("get unused machines failed %s", err.Error())
		return err
	}
	allowCCMouduleInfo, err = meta.GetDbmEnv()
	if err != nil {
		logger.Error("get dbm env failed %s", err.Error())
		return err
	}
	logger.Info("空闲模块id %v", allowCCMouduleInfo.CC_IDLE_MODULE_ID)
	logger.Info("资源模块信息 %v", allowCCMouduleInfo.CC_MANAGE_TOPO)
	client, err := bk.NewClient()
	if err != nil {
		logger.Error("new bk client failed %s", err.Error())
		return err
	}
	hostIdMap := make(map[int][]int)
	for _, machine := range machines {
		hostIdMap[machine.BkBizId] = append(hostIdMap[machine.BkBizId], machine.BkHostID)
	}
	for bkBizId, hostIds := range hostIdMap {
		for _, hostgp := range cmutil.SplitGroup(hostIds, 100) {
			resp, ori, err := cc.NewFindHostTopoRelation(client).Query(&cc.FindHostTopoRelationParam{
				BkBizID:   bkBizId,
				BkHostIds: hostgp,
				Page: cc.BKPage{
					Start: 0,
					Limit: 100,
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
			for _, m := range resp.Data {
				if m.BKModuleId == allowCCMouduleInfo.CC_IDLE_MODULE_ID {
					continue
				}
				if m.BKSetId == allowCCMouduleInfo.CC_MANAGE_TOPO.SetId {
					continue
				}
				err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_biz_id = ? and bk_host_id = ? and  status = ? ",
					bkBizId,
					m.BKHostId, model.Unused).
					Update("status", model.UsedByOther).Error
				if err != nil {
					logger.Error("update machine status failed %s", err.Error())
					return err
				}
			}
		}
	}
	return nil
}
