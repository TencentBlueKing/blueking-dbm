/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package task TODO
package task

import (
	"fmt"
	"runtime/debug"
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// ApplyResponeLogItem TODO
type ApplyResponeLogItem struct {
	RequestId string
	Data      []model.BatchGetTbDetailResult
}

// ApplyResponeLogChan TODO
var ApplyResponeLogChan chan ApplyResponeLogItem

// ArchiverResourceChan TODO
var ArchiverResourceChan chan int

// RecordRsOperatorInfoChan TODO
var RecordRsOperatorInfoChan chan model.TbRpOperationInfo

// SyncRsGseAgentStatusChan TODO
var SyncRsGseAgentStatusChan chan []string

// RuningTask TODO
var RuningTask chan struct{}

func init() {
	ApplyResponeLogChan = make(chan ApplyResponeLogItem, 100)
	ArchiverResourceChan = make(chan int, 200)
	RecordRsOperatorInfoChan = make(chan model.TbRpOperationInfo, 20)
	RuningTask = make(chan struct{}, 100)
	SyncRsGseAgentStatusChan = make(chan []string, 10)
}

// init TODO
// StartTask 异步写日志
func init() {
	defer func() {
		if r := recover(); r != nil {
			logger.Error("panic error:%v,stack:%s", r, string(debug.Stack()))
			return
		}
	}()
	go func() {
		var archIds []int
		ticker := time.NewTicker(10 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case d := <-ApplyResponeLogChan:
				err := recordTask(d)
				if err != nil {
					logger.Error("record log failed, %s", err.Error())
				}
			case id := <-ArchiverResourceChan:
				if len(RuningTask) > 0 {
					archIds = append(archIds, id)
				} else {
					archIds = append(archIds, id)
					if err := archiverResource(archIds); err != nil {
						logger.Warn("archiver resouce failed %s", err.Error())
					}
					archIds = []int{}
				}
			case <-ticker.C:
				if len(RuningTask) <= 0 && len(archIds) > 0 {
					if err := archiverResource(archIds); err != nil {
						logger.Warn("archiver resouce failed %s", err.Error())
					}
					archIds = []int{}
				}
			case info := <-RecordRsOperatorInfoChan:
				if err := recordRsOperationInfo(info); err != nil {
					logger.Error("failed to record resource operation log %s", err.Error())
				}
			case agentIds := <-SyncRsGseAgentStatusChan:
				if err := UpdateResourceGseAgentStatus(agentIds...); err != nil {
					logger.Warn("[sync task]: sync gse agent status failed:%s", err.Error())
				}
			}
		}
	}()
}

// archiverResource 异步归档资源
func archiverResource(ids []int) (err error) {
	return model.ArchiverResouce(ids)
}

func recordTask(data ApplyResponeLogItem) error {
	if data.Data == nil {
		return fmt.Errorf("data is nill")
	}
	m := []model.TbRpApplyDetailLog{}
	for _, v := range data.Data {
		for _, vv := range v.Data {
			m = append(m, model.TbRpApplyDetailLog{
				RequestID:  data.RequestId,
				IP:         vv.IP,
				BkCloudID:  vv.BkCloudID,
				Item:       v.Item,
				BkHostID:   vv.BkHostID,
				UpdateTime: time.Now(),
				CreateTime: time.Now(),
			})
			logger.Debug("%s -- %s -- %s -- %s", v.Item, vv.IP, vv.RackID, vv.NetDeviceID)
		}
	}
	return model.CreateBatchTbRpOpsAPIDetailLog(m)
}

func recordRsOperationInfo(data model.TbRpOperationInfo) (err error) {
	return model.DB.Self.Table(model.TbRpOperationInfoTableName()).Create(&data).Error
}

// UpdateResourceGseAgentStatus TODO
func UpdateResourceGseAgentStatus(agentIds ...string) (err error) {
	var agentIdList []string
	db := model.DB.Self.Table(model.TbRpDetailName()).Select("bk_agent_id").Where(
		"status = ? and agent_status_update_time < date_sub(now(),INTERVAL 5 MINUTE)", model.Unused)
	if len(agentIds) > 0 {
		db.Where("bk_agent_id in (?)", agentIds)
	}
	if err = db.Scan(&agentIdList).Error; err != nil {
		logger.Error("query resoure list failed %s", err.Error())
		return err
	}
	for _, gseAgentIdlist := range cmutil.SplitGroup(agentIdList, 1000) {
		agentStateList, resp, err := cc.NewListAgentState(bk.GseClient).QueryListAgentInfo(&cc.ListAgentInfoParam{
			AgentIdList: gseAgentIdlist,
		})
		if err != nil {
			var BkRequestId, BkMessage string
			if resp != nil {
				BkRequestId = resp.RequestId
				BkMessage = resp.Message
			}
			logger.Error("query gse agent state failed %s;blueking trace id:%s,msg:%s", err.Error(), BkRequestId,
				BkMessage)
			return err
		}
		for _, agentState := range agentStateList {
			agentId := agentState.BkAgentId
			if cmutil.IsEmpty(agentId) {
				agentId = fmt.Sprintf("%d:%s", agentState.BkCloudID, agentState.BkHostIp)
			}
			err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_agent_id = ? ", agentId).Updates(map[string]interface{}{
				"gse_agent_status_code": agentState.StatusCode, "agent_status_update_time": time.Now()}).Error
			if err != nil {
				logger.Error("update gse agent status failed %s", err.Error())
				continue
			}
		}
	}
	return nil
}
