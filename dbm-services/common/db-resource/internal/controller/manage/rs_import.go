/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package manage

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/cloud"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"

	rf "github.com/gin-gonic/gin"
)

// ImportMachParam TODO
type ImportMachParam struct {
	BkCloudId int `json:"bk_cloud_id"`
	// ForBizs 业务标签,表示这个资源将来给ForBizs这个业务使用
	ForBizs []int             `json:"for_bizs"`
	RsTypes []string          `json:"resource_types"`
	BkBizId int               `json:"bk_biz_id"  binding:"number"`
	Hosts   []HostBase        `json:"hosts" binding:"gt=0,dive,required"`
	Labels  map[string]string `json:"labels"`
	apply.ActionInfo
}

// HostBase TODO
type HostBase struct {
	Ip     string `json:"ip"  binding:"required,ip"`
	HostId int    `json:"host_id" binding:"required"`
}

func (p ImportMachParam) getOperationInfo(requestId string, hostIds json.RawMessage,
	iplist json.RawMessage) model.TbRpOperationInfo {
	return model.TbRpOperationInfo{
		RequestID:     requestId,
		OperationType: model.Imported,
		TotalCount:    len(p.getIps()),
		TaskId:        p.TaskId,
		BillId:        p.BillId,
		Operator:      p.Operator,
		CreateTime:    time.Now(),
		BkHostIds:     hostIds,
		IpList:        iplist,
		UpdateTime:    time.Now(),
	}
}

func (p ImportMachParam) getIps() (ips []string) {
	for _, v := range p.Hosts {
		if !cmutil.IsEmpty(v.Ip) {
			ips = append(ips, v.Ip)
		}
	}
	return
}

func (p ImportMachParam) getHostIds() (hostIds []int) {
	for _, v := range p.Hosts {
		if v.HostId > 0 {
			hostIds = append(hostIds, v.HostId)
		}
	}
	return
}

func (p *ImportMachParam) existCheck() (err error) {
	var alreadyExistRs []model.TbRpDetail
	err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_cloud_id = ? and ip in (?)", p.BkCloudId, p.getIps()).
		Scan(&alreadyExistRs).Error
	if err != nil {
		return errno.ErrDBQuery.Add(err.Error())
	}
	if len(alreadyExistRs) > 0 {
		errMsg := "already exist:\n "
		for _, r := range alreadyExistRs {
			errMsg += fmt.Sprintf(" bk_cloud_id:%d,ip:%s \n", r.BkCloudID, r.IP)
		}
		return fmt.Errorf(errMsg)
	}
	return nil
}

// Import TODO
func (c *MachineResourceHandler) Import(r *rf.Context) {
	var input ImportMachParam
	if err := c.Prepare(r, &input); err != nil {
		logger.Error(fmt.Sprintf("Preare Error %s", err.Error()))
		return
	}
	requestId := r.GetString("request_id")
	if err := input.existCheck(); err != nil {
		c.SendResponse(r, errno.RepeatedIpExistSystem.Add(err.Error()), requestId, err.Error())
		return
	}
	resp, err := Doimport(input)
	if err != nil {
		logger.Error(fmt.Sprintf("ImportByIps failed %s", err.Error()))
		c.SendResponse(r, err, requestId, err.Error())
		return
	}
	if len(resp.NotFoundInCCHosts) == len(input.Hosts) {
		c.SendResponse(r, fmt.Errorf("all machines failed to query cmdb information"), resp, requestId)
		return
	}
	hostIds, err := json.Marshal(input.getHostIds())
	if err != nil {
		c.SendResponse(r, errno.ErrJSONMarshal.Add("input bkhostIds"), resp, requestId)
		return
	}
	iplist, err := json.Marshal(input.getIps())
	if err != nil {
		c.SendResponse(r, errno.ErrJSONMarshal.Add("input ips"), resp, requestId)
		return
	}
	task.RecordRsOperatorInfoChan <- input.getOperationInfo(requestId, hostIds, iplist)
	c.SendResponse(r, err, resp, requestId)
}

// ImportHostResp TODO
type ImportHostResp struct {
	GetDiskInfoJobErrMsg string            `json:"get_disk_job_errmsg"`
	SearchDiskErrInfo    map[string]string `json:"search_disk_err_info"`
	NotFoundInCCHosts    []string          `json:"not_found_in_cc_hosts"`
}

func (p ImportMachParam) transParamToBytes() (lableJson, bizJson, rstypes json.RawMessage, err error) {
	lableJson = []byte("{}")
	lableJson, err = json.Marshal(cmutil.CleanStrMap(p.Labels))
	if err != nil {
		logger.Error(fmt.Sprintf("ConverLableToJsonStr Failed,Error:%s", err.Error()))
		return
	}
	bizJson = []byte("[]")
	if len(p.ForBizs) > 0 {
		bizJson, err = json.Marshal(cmutil.IntSliceToStrSlice(p.ForBizs))
		if err != nil {
			logger.Error(fmt.Sprintf("conver biz json Failed,Error:%s", err.Error()))
			return
		}
	}
	rstypes = []byte("[]")
	if len(p.RsTypes) > 0 {
		rstypes, err = json.Marshal(p.RsTypes)
		if err != nil {
			logger.Error(fmt.Sprintf("conver resource types Failed,Error:%s", err.Error()))
			return
		}
	}
	return
}

// Doimport TODO
func Doimport(param ImportMachParam) (resp *ImportHostResp, err error) {
	var ccHostsInfo []*cc.Host
	var derr error
	var diskResp bk.GetDiskResp
	var notFoundHosts, gseAgentIds []string
	var elems []model.TbRpDetail
	resp = &ImportHostResp{}
	wg := sync.WaitGroup{}
	targetHosts := cmutil.RemoveDuplicate(param.getIps())

	wg.Add(1)
	go func() {
		defer wg.Done()
		ccHostsInfo, notFoundHosts, derr = bk.BatchQueryHostsInfo(param.BkBizId, targetHosts)
	}()
	// get disk information in batch
	diskResp, err = bk.GetDiskInfo(targetHosts, param.BkCloudId, param.BkBizId)
	if err != nil {
		logger.Error("query host cc info failed %s", err.Error())
		return resp, err
	}
	wg.Wait()
	resp.SearchDiskErrInfo = diskResp.IpFailedLogMap
	resp.NotFoundInCCHosts = notFoundHosts
	if derr != nil {
		logger.Error("search disk info by job  failed %s", derr.Error())
		resp.GetDiskInfoJobErrMsg = derr.Error()
		// return
	}
	if len(notFoundHosts) >= len(param.Hosts) {
		return resp, fmt.Errorf("all hosts query empty in cc")
	}

	lableJson, bizJson, rstypes, err := param.transParamToBytes()
	if err != nil {
		return resp, err
	}
	hostsMap := make(map[string]struct{})
	for _, host := range targetHosts {
		hostsMap[host] = struct{}{}
	}
	for _, emptyhost := range notFoundHosts {
		delete(hostsMap, emptyhost)
	}
	// further probe disk specific information
	probeFromCloud(diskResp.IpLogContentMap)
	logger.Info("more info %v", ccHostsInfo)
	for _, h := range ccHostsInfo {
		delete(hostsMap, h.InnerIP)
		el := transHostInfoToDbModule(h, param.BkCloudId, param.BkBizId, rstypes, bizJson, lableJson)
		el.SetMore(h.InnerIP, diskResp.IpLogContentMap)
		// gse agent 1.0的 agent 是用 cloudid:ip
		gseAgentId := h.BkAgentId
		if cmutil.IsEmpty(gseAgentId) {
			gseAgentId = fmt.Sprintf("%d:%s", param.BkCloudId, h.InnerIP)
		}
		gseAgentIds = append(gseAgentIds, gseAgentId)
		el.BkAgentId = gseAgentId
		elems = append(elems, el)
	}
	if err := model.DB.Self.Table(model.TbRpDetailName()).Create(elems).Error; err != nil {
		logger.Error("failed to save resource: %s", err.Error())
		return resp, err
	}
	task.SyncRsGseAgentStatusChan <- gseAgentIds
	return resp, err
}

func transHostInfoToDbModule(h *cc.Host, bkCloudId, bkBizId int, rstp, biz, label []byte) model.TbRpDetail {
	return model.TbRpDetail{
		RsTypes:         rstp,
		DedicatedBizs:   biz,
		BkCloudID:       bkCloudId,
		BkBizId:         bkBizId,
		AssetID:         h.AssetID,
		BkHostID:        h.BKHostId,
		IP:              h.InnerIP,
		Label:           label,
		DeviceClass:     h.DeviceClass,
		DramCap:         h.BkMem,
		CPUNum:          h.BkCpu,
		City:            h.IdcCityName,
		CityID:          h.IdcCityId,
		SubZone:         h.SZone,
		SubZoneID:       h.SZoneID,
		RackID:          h.Equipment,
		SvrTypeName:     h.SvrTypeName,
		Status:          model.Unused,
		NetDeviceID:     h.LinkNetdeviceId,
		StorageDevice:   []byte("{}"),
		TotalStorageCap: h.BkDisk,
		BkAgentId:       h.BkAgentId,
		AgentStatusCode: 2,
		UpdateTime:      time.Now(),
		CreateTime:      time.Now(),
	}
}

// probeFromCloud Detect The Disk Type Again Through The Cloud Interface
func probeFromCloud(diskMap map[string]*bk.ShellResCollection) {
	var clouder cloud.Disker
	var err error
	if clouder, err = cloud.NewDisker(); err != nil {
		return
	}
	ctr := make(chan struct{}, 5)
	wg := sync.WaitGroup{}
	for ip := range diskMap {
		// if the disk id and region obtained by job are all empty skip the request for cloud api
		ctr <- struct{}{}
		wg.Add(1)
		go func(ip string) {
			defer func() { wg.Done(); <-ctr }()
			dkinfo := diskMap[ip]
			diskIds := bk.GetAllDiskIds(dkinfo.Disk)
			if cmutil.IsEmpty(dkinfo.TxRegion) || len(diskIds) <= 0 {
				return
			}
			cloudInfo, err := clouder.DescribeDisk(diskIds, dkinfo.TxRegion)
			if err != nil {
				logger.Error("call clouder describe disk info failed %s", err.Error())
				return
			}
			for _, dk := range dkinfo.Disk {
				if v, ok := cloudInfo[dk.DiskId]; ok {
					dk.DiskType = v
				}
			}
		}(ip)
	}
	wg.Wait()
}
