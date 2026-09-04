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
	"database/sql"
	"encoding/json"
	"fmt"
	"runtime/debug"
	"time"

	"github.com/samber/lo"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/dbmapi"
	"dbm-services/common/db-resource/internal/util"
	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

// ApplyResponseLogItem apply response log item
type ApplyResponseLogItem struct {
	RequestId string
	Data      []model.BatchGetTbDetailResult
}

// AnalysisTaskItem 智能体分析任务项
type AnalysisTaskItem struct {
	BillID      string
	ApplyParams json.RawMessage
	// Evidence 申请失败现场(apply.ApplyFailureEvidence 的 JSON),可为空
	Evidence json.RawMessage
}

// ApplyResponseLogChan apply response log channel
var ApplyResponseLogChan chan ApplyResponseLogItem

// ArchivedResourceChan archived resource channel
var ArchivedResourceChan chan int

// RecordRsOperatorInfoChan TODO
var RecordRsOperatorInfoChan chan model.TbRpOperationInfo

// SyncRsGseAgentStatusChan TODO
var SyncRsGseAgentStatusChan chan []int

// AnalysisTaskChan 智能体分析任务 channel
var AnalysisTaskChan chan AnalysisTaskItem

func init() {
	ApplyResponseLogChan = make(chan ApplyResponseLogItem, 100)
	ArchivedResourceChan = make(chan int, 500)
	RecordRsOperatorInfoChan = make(chan model.TbRpOperationInfo, 20)
	SyncRsGseAgentStatusChan = make(chan []int, 10)
	AnalysisTaskChan = make(chan AnalysisTaskItem, 50)
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
		const archiveMaxAttempts = 3
		const archiveRetryInterval = time.Second

		// flushArchive 批量归档队列中的资源；失败时有限次立即重试，仍失败则保留 ID 待下次入队触发。
		flushArchive := func(trigger string) {
			if len(archIds) == 0 {
				return
			}
			ids := lo.Uniq(archIds)
			for attempt := 1; attempt <= archiveMaxAttempts; attempt++ {
				logger.Info("[archive] start flush, trigger=%s, attempt=%d/%d, count=%d, ids=%v",
					trigger, attempt, archiveMaxAttempts, len(ids), ids)
				if err := archiveResource(ids); err != nil {
					logger.Warn("[archive] flush failed, trigger=%s, attempt=%d/%d, count=%d, ids=%v, err=%s",
						trigger, attempt, archiveMaxAttempts, len(ids), ids, err.Error())
					if attempt < archiveMaxAttempts {
						time.Sleep(archiveRetryInterval)
						continue
					}
					archIds = ids
					return
				}
				logger.Info("[archive] flush succeed, trigger=%s, count=%d", trigger, len(ids))
				archIds = nil
				return
			}
		}

		for {
			select {
			case d := <-ApplyResponseLogChan:
				err := recordTask(d)
				if err != nil {
					logger.Error("record log failed, %s", err.Error())
				}
			case id := <-ArchivedResourceChan:
				archIds = append(archIds, id)
				logger.Info("[archive] enqueue id=%d, pending=%d", id, len(archIds))
				flushArchive("resource_enqueued")
			case info := <-RecordRsOperatorInfoChan:
				if err := recordRsOperationInfo(info); err != nil {
					logger.Error("failed to record resource operation log %s", err.Error())
				}
			case agentIds := <-SyncRsGseAgentStatusChan:
				if err := UpdateResourceGseAgentStatus(agentIds...); err != nil {
					logger.Warn("[sync task]: sync gse agent status failed:%s", err.Error())
				}
			case analysisTask := <-AnalysisTaskChan:
				if ProcessAnalysisTask != nil {
					go ProcessAnalysisTask(analysisTask)
				} else {
					logger.Warn("ProcessAnalysisTask is not initialized, skip analysis task for bill %s", analysisTask.BillID)
				}
			}
		}
	}()
}

// archiveResource 异步归档资源
func archiveResource(ids []int) (err error) {
	return model.ArchiveResource(ids)
}

func recordTask(data ApplyResponseLogItem) error {
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

// UpdateResourceGseAgentStatus 更新gse状态
func UpdateResourceGseAgentStatus(bkHostIds ...int) (err error) {
	if config.AppConfig.BkNodeManApiUrl == "" {
		logger.Warn("BK NodeMan API URL 为空，不更新 GSE 状态")
		return nil
	}
	var unUsedRsList []model.TbRpDetail
	db := model.DB.Self.Table(model.TbRpDetailName()).Where(
		"status = ? and agent_status_update_time < date_sub(now(),INTERVAL 30 MINUTE)", model.Unused)
	if len(bkHostIds) > 0 {
		db.Where("bk_host_id in (?)", bkHostIds)
	}
	if err = db.Scan(&unUsedRsList).Error; err != nil {
		logger.Error("query resource list failed %s", err.Error())
		return err
	}
	pl := make(map[int][]cc.IpchooserHost)
	for _, rs := range unUsedRsList {
		pl[rs.BkBizId] = append(pl[rs.BkBizId], cc.IpchooserHost{
			HostId: rs.BkHostID,
			Meta: cc.IpchooserHostMeta{
				ScopeType: "biz",
				ScopeId:   fmt.Sprintf("%d", rs.BkBizId),
				BkBizId:   rs.BkBizId,
			},
		})
	}

	for bkbizId, ipchooserHostsList := range pl {
		for _, ipchooserHosts := range lo.Chunk(ipchooserHostsList, 200) {
			agentStateList, resp, err := cc.NewListAgentState(bk.BkNodeManClient).QueryListAgentInfo(&cc.ListAgentInfoParam{
				HostList: ipchooserHosts,
				ScopeList: []cc.Scope{
					{
						ScopeType: "biz",
						ScopeId:   fmt.Sprintf("%d", bkbizId),
					},
				},
			})
			if err != nil {
				var BkRequestId, BkMessage string
				if resp != nil {
					BkRequestId = resp.RequestId
					BkMessage = resp.Message
				}
				logger.Error("query ipchooser device failed %s;blueking trace id:%s,msg:%s", err.Error(), BkRequestId,
					BkMessage)
				return err
			}
			for _, agentState := range agentStateList {
				err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_host_id = ? ", agentState.HostId).
					Updates(map[string]interface{}{
						"bk_agent_id":              agentState.BkAgentId,
						"gse_agent_status_code":    agentState.BkAgentAlive,
						"agent_status_update_time": time.Now()}).Error
				if err != nil {
					logger.Error("update gse agent status failed %s", err.Error())
					continue
				}
			}
		}
	}
	return nil
}

// AsyncBkCmdbAttributes 异步同步主机CMDB属性
func AsyncBkCmdbAttributes() (err error) {
	logger.Info("start async from cmdb ...")
	allowCCModuleInfo, err := dbmapi.GetDbmEnv()
	if err != nil {
		logger.Error("get dbm env failed %s", err.Error())
		return err
	}
	resourceBizID := allowCCModuleInfo.RESOURCE_INDEPENDENT_BIZ
	logger.Info("resource independent biz id %d", resourceBizID)

	var rsList []model.TbRpDetail
	err = model.DB.Self.Table(model.TbRpDetailName()).Select("ip").Find(&rsList).Error
	if err != nil {
		if err == sql.ErrNoRows {
			return nil
		}
		logger.Error("query resource list failed, err %w ", err)
		return err
	}
	if len(rsList) == 0 {
		return nil
	}
	hosts := make([]string, 0, len(rsList))
	for _, rs := range rsList {
		hosts = append(hosts, rs.IP)
	}
	logger.Info("sync cmdb attributes for %d hosts in resource pool", len(hosts))

	ccInfos, notFoundHosts, err := bk.BatchQueryHostsInfo(resourceBizID, hosts)
	if err != nil {
		logger.Warn("query machine host info from cmdb failed, biz_id:%d, err:%s", resourceBizID, err.Error())
		return err
	}
	if len(notFoundHosts) > 0 {
		logger.Warn("hosts not found in cmdb, biz_id:%d, count:%d, hosts:%v", resourceBizID, len(notFoundHosts), notFoundHosts)
	}
	for _, ccInfo := range ccInfos {
		updates := map[string]interface{}{
			"city":           ccInfo.IdcCityName,
			"city_id":        ccInfo.IdcCityId,
			"sub_zone":       ccInfo.SZone,
			"sub_zone_id":    ccInfo.SZoneID,
			"rack_id":        util.CleanStr(ccInfo.Equipment),
			"net_device_id":  util.TransInnerSwitchIpAsNetDeviceId(ccInfo.InnerSwitchIp),
			"os_name":        util.CleanOsName(ccInfo.OSName),
			"os_version":     ccInfo.BkOsVersion,
			"os_name_origin": ccInfo.OSName,
			"idc_id":         ccInfo.IDCID,
			"idc_name":       ccInfo.IDC,
		}
		// 空值不覆盖：CMDB 未返回母机固资号时保留库内已有值
		if cmutil.IsNotEmpty(ccInfo.BkSvrOwnerAssetID) {
			updates["bk_svr_owner_asset_id"] = ccInfo.BkSvrOwnerAssetID
		}
		if ccInfo.BkDisk > 0 {
			updates["total_storage_cap"] = ccInfo.BkDisk
		}
		err = model.DB.Self.Table(model.TbRpDetailName()).Where("ip = ?", ccInfo.InnerIP).
			Updates(updates).Error
		if err != nil {
			logger.Warn("request cmdb api failed %s", err.Error())
		}
	}
	return nil
}

// SyncOsNameInfo sync os name info
func SyncOsNameInfo() (err error) {
	logger.Info("start async from cmdb ...")
	var rsList []model.TbRpDetail
	err = model.DB.Self.Table(model.TbRpDetailName()).Find(&rsList).Error
	if err != nil {
		if err == sql.ErrNoRows {
			return nil
		}
		logger.Error("query resource list failed, err %w ", err)
		return err
	}
	bizHostMap := make(map[int][]string)
	for _, rs := range rsList {
		bizHostMap[rs.BkBizId] = append(bizHostMap[rs.BkBizId], rs.IP)
	}
	for bizId, hosts := range bizHostMap {
		ccInfos, _, err := bk.BatchQueryHostsInfo(bizId, hosts)
		if err != nil {
			logger.Warn("query machine hardinfo from cmdb failed %s", err.Error())
			continue
		}
		for _, ccInfo := range ccInfos {
			err = model.DB.Self.Table(model.TbRpDetailName()).Where("ip = ? and  bk_biz_id = ? ", ccInfo.InnerIP, bizId).
				Updates(map[string]interface{}{
					"os_name":        util.CleanOsName(ccInfo.OSName),
					"os_version":     ccInfo.BkOsVersion,
					"os_name_origin": ccInfo.OSName,
				}).Error
			if err != nil {
				logger.Warn("request cmdb api failed %s", err.Error())
			}
		}
	}
	return nil
}

// FlushNetDeviceInfo 刷新网络设备信息
func FlushNetDeviceInfo() (err error) {
	var rsList []model.TbRpDetail
	err = model.DB.Self.Table(model.TbRpDetailName()).Find(&rsList).Error
	if err != nil {
		if err == sql.ErrNoRows {
			return nil
		}
		logger.Error("query resource list failed, err %w ", err)
		return err
	}
	bizHostMap := make(map[int][]string)
	for _, rs := range rsList {
		bizHostMap[rs.BkBizId] = append(bizHostMap[rs.BkBizId], rs.IP)
	}
	for bizId, hosts := range bizHostMap {
		ccInfos, _, err := bk.BatchQueryHostsInfo(bizId, hosts)
		if err != nil {
			logger.Warn("query machine hardinfo from cmdb failed %s", err.Error())
			continue
		}
		for _, ccInfo := range ccInfos {
			err = model.DB.Self.Table(model.TbRpDetailName()).Where("ip = ? and  bk_biz_id = ? ", ccInfo.InnerIP, bizId).
				Updates(map[string]interface{}{
					"net_device_id": util.TransInnerSwitchIpAsNetDeviceId(ccInfo.InnerSwitchIp),
				}).Error
			if err != nil {
				logger.Warn("request cmdb api failed %s", err.Error())
			}
		}
	}
	return nil
}

// ProcessAnalysisTask 处理智能体分析任务（由 agent 包实现）
// 此函数声明在这里，但实际实现在 agent 包中以避免循环导入
var ProcessAnalysisTask func(task AnalysisTaskItem)

// SetAnalysisTaskProcessor 设置分析任务处理器（在 main.go 中调用）
func SetAnalysisTaskProcessor(processor func(task AnalysisTaskItem)) {
	ProcessAnalysisTask = processor
}
