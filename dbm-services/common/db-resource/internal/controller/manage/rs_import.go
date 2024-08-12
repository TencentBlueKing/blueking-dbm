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
	"regexp"
	"strings"
	"time"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/db-resource/internal/svr/bk"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/db-resource/internal/svr/yunti"
	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"

	rf "github.com/gin-gonic/gin"
	"github.com/samber/lo"
)

// ImportMachParam 资源导入请求参数
type ImportMachParam struct {
	// ForBizs 业务标签,表示这个资源将来给ForBizs这个业务使用
	ForBiz  int               `json:"for_biz"`
	RsType  string            `json:"resource_type"`
	BkBizId int               `json:"bk_biz_id"  binding:"number"`
	Hosts   []HostBase        `json:"hosts" binding:"gt=0,dive,required"`
	Labels  map[string]string `json:"labels"`
	apply.ActionInfo
}

// HostBase 主机基本请求参数
type HostBase struct {
	Ip        string `json:"ip"  binding:"required,ip"`
	HostId    int    `json:"host_id" binding:"required"`
	BkCloudId int    `json:"bk_cloud_id"`
}

// getIps 从参数中获取ipList
func (p ImportMachParam) getIps() []string {
	return lo.FilterMap(p.Hosts, func(item HostBase, _ int) (string, bool) {
		return item.Ip, lo.IsNotEmpty(item.Ip)
	})
}

func (p ImportMachParam) getIpsByCloudId() (ipMap map[int][]string) {
	ipMap = make(map[int][]string)
	for _, v := range p.Hosts {
		if !cmutil.IsEmpty(v.Ip) {
			ipMap[v.BkCloudId] = append(ipMap[v.BkCloudId], v.Ip)
		}
	}
	return
}

// existCheck 导入前存在性检查
func (p *ImportMachParam) existCheck() (err error) {
	var alreadyExistRs []model.TbRpDetail
	ipmap := p.getIpsByCloudId()
	for cloudId, ips := range ipmap {
		err = model.DB.Self.Table(model.TbRpDetailName()).Where("bk_cloud_id = ? and ip in (?)", cloudId, ips).
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
	}
	return nil
}

// Import 导入主机资源
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
	c.SendResponse(r, err, resp, requestId)
}

// ImportHostResp 导入主机参数
type ImportHostResp struct {
	GetDiskInfoJobErrMsg string            `json:"get_disk_job_errmsg"`
	SearchDiskErrInfo    map[string]string `json:"search_disk_err_info"`
	NotFoundInCCHosts    []string          `json:"not_found_in_cc_hosts"`
}

func (p ImportMachParam) transParamToBytes() (lableJson json.RawMessage, err error) {
	// lableJson = []byte("{}")
	lableJson, err = json.Marshal(cmutil.CleanStrMap(p.Labels))
	if err != nil {
		logger.Error(fmt.Sprintf("ConverLableToJsonStr Failed,Error:%s", err.Error()))
		return
	}
	return
}

func (p ImportMachParam) getJobIpList() (ipList []bk.IPList) {
	return lo.Map(p.Hosts, func(host HostBase, _ int) bk.IPList {
		return bk.IPList{
			IP:        host.Ip,
			BkCloudID: host.BkCloudId,
		}
	})
}

// Doimport 导入主机获取主机信息
func Doimport(param ImportMachParam) (resp *ImportHostResp, err error) {
	var ccHostsInfo []*cc.Host
	var derr error
	var diskResp bk.GetDiskResp
	var notFoundHosts, gseAgentIds []string
	var elems []model.TbRpDetail
	resp = &ImportHostResp{}
	targetHosts := cmutil.RemoveDuplicate(param.getIps())
	ccHostsInfo, notFoundHosts, derr = bk.BatchQueryHostsInfo(param.BkBizId, targetHosts)
	if derr != nil {
		logger.Error("query cc info from cmdb failed %s", derr.Error())
		resp.GetDiskInfoJobErrMsg = derr.Error()
		return resp, err
	}
	if len(notFoundHosts) >= len(param.Hosts) {
		return resp, fmt.Errorf("all hosts cannot query any information in cmdb~")
	}
	hostOsMap := lo.SliceToMap(ccHostsInfo, func(item *cc.Host) (string, string) {
		return item.InnerIP, model.ConvertOsTypeToHuman(item.BkOsType)
	})
	diskResp, err = bk.GetDiskInfo(param.getJobIpList(), param.BkBizId, hostOsMap)
	if err != nil {
		logger.Error("get disk info failed %s", err.Error())
		return resp, fmt.Errorf("execute job get disk info failed %w", err)
	}
	resp.SearchDiskErrInfo = diskResp.IpFailedLogMap
	resp.NotFoundInCCHosts = notFoundHosts
	lableJson, err := param.transParamToBytes()
	if err != nil {
		return resp, err
	}
	hostsMap := lo.SliceToMap(targetHosts, func(item string) (string, struct{}) { return item, struct{}{} })
	for _, emptyhost := range notFoundHosts {
		delete(hostsMap, emptyhost)
	}
	logger.Info("yunti config  %v", config.AppConfig.Yunti)
	// if yunti config is not empty
	var cvmInfoMap map[string]yunti.InstanceDetail
	if config.AppConfig.Yunti.IsNotEmpty() {
		logger.Info("try to get machine info from yunti")
		var verr error
		cvmInfoMap, verr = getCvmMachDetailInfo(getCvmMachList(ccHostsInfo))
		if verr != nil {
			logger.Warn("query cvm info failed %s", verr.Error())
		}
	}
	for _, h := range ccHostsInfo {
		delete(hostsMap, h.InnerIP)
		el := param.transHostInfoToDbModule(h, h.BkCloudId, lableJson)
		el.SetMore(h.InnerIP, diskResp.IpLogContentMap)
		// gse agent 1.0的 agent 是用 cloudid:ip
		gseAgentId := h.BkAgentId
		if cmutil.IsEmpty(gseAgentId) {
			gseAgentId = fmt.Sprintf("%d:%s", h.BkCloudId, h.InnerIP)
		}
		gseAgentIds = append(gseAgentIds, gseAgentId)
		el.BkAgentId = gseAgentId
		if v, ok := cvmInfoMap[h.InnerIP]; ok {
			el.DramCap = v.Memory * 1000
		}
		elems = append(elems, el)
	}
	if err = model.DB.Self.Table(model.TbRpDetailName()).Create(elems).Error; err != nil {
		logger.Error("failed to save resource: %s", err.Error())
		return resp, err
	}
	task.SyncRsGseAgentStatusChan <- gseAgentIds
	return resp, err
}

// getCvmMachDetailInfo 获取cvm的相关的信息
func getCvmMachDetailInfo(ipList []string) (cvmInfoMap map[string]yunti.InstanceDetail, err error) {
	cvmInfoMap = make(map[string]yunti.InstanceDetail)
	if len(ipList) == 0 {
		return cvmInfoMap, nil
	}
	resp, err := config.AppConfig.Yunti.QueryCVMInstances(ipList)
	if err != nil {
		return cvmInfoMap, err
	}

	logger.Info("get total  %d machines by yunti", resp.Result.Total)
	return lo.SliceToMap(resp.Result.Data, func(item yunti.InstanceDetail) (string, yunti.InstanceDetail) {
		return item.LanIp, item
	}), nil
}

func regularExpressionMatching(regular, s string) bool {
	m, err := regexp.MatchString(regular, s)
	if err != nil {
		logger.Error("matching error: %s", err.Error())
		return false
	}
	return m
}

// getCvmMachList 判断主机是否是cvm
func getCvmMachList(hosts []*cc.Host) []string {
	var machIpList []string
	for _, host := range hosts {
		if regularExpressionMatching(`^TC(\d*)\d$`, host.AssetID) || strings.Contains(strings.ToUpper(host.SvrTypeName),
			"QC_CVM") {
			machIpList = append(machIpList, host.InnerIP)
		}
	}
	return machIpList
}

// transHostInfoToDbModule 获取的到的主机信息赋值给db model
func (p ImportMachParam) transHostInfoToDbModule(h *cc.Host, bkCloudId int, label []byte) model.TbRpDetail {
	osType := h.BkOsType
	if cmutil.IsEmpty(osType) {
		osType = bk.OsLinux
	}
	return model.TbRpDetail{
		DedicatedBiz:    p.ForBiz,
		RsType:          p.RsType,
		BkCloudID:       bkCloudId,
		BkBizId:         p.BkBizId,
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
		RackID:          strings.TrimSpace(h.Equipment),
		SvrTypeName:     h.SvrTypeName,
		Status:          model.Unused,
		NetDeviceID:     strings.TrimSpace(h.LinkNetdeviceId),
		StorageDevice:   []byte("{}"),
		TotalStorageCap: h.BkDisk,
		BkAgentId:       h.BkAgentId,
		AgentStatusCode: 2,
		OsType:          model.ConvertOsTypeToHuman(osType),
		OsBit:           h.BkOsBit,
		OsVerion:        h.BkOsVersion,
		OsName:          strings.TrimSpace(strings.ToLower(strings.ReplaceAll(h.OSName, " ", ""))),
		UpdateTime:      time.Now(),
		CreateTime:      time.Now(),
	}
}
