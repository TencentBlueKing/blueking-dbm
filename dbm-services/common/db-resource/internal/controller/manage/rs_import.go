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
	"dbm-services/common/db-resource/internal/util"
	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/common/go-pubpkg/logger"

	rf "github.com/gin-gonic/gin"
	"github.com/samber/lo"
)

// ImportMachParam 资源导入请求参数
type ImportMachParam struct {
	// ForBizs 业务标签,表示这个资源将来给ForBizs这个业务使用
	ForBiz  int        `json:"for_biz"`
	RsType  string     `json:"resource_type"`
	BkBizId int        `json:"bk_biz_id"  binding:"number"`
	Hosts   []HostBase `json:"hosts" binding:"gt=0,dive,required"`
	Labels  []string   `json:"labels"`
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
		if lo.IsNotEmpty(v.Ip) {
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
			return fmt.Errorf("%s", errMsg)
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
	if err := input.existCheck(); err != nil {
		c.SendResponse(r, errno.RepeatedIpExistSystem.Add(err.Error()), err.Error())
		return
	}
	resp, err := Doimport(input, c.RequestId)
	if err != nil {
		logger.Error(fmt.Sprintf("ImportByIps failed %s", err.Error()))
		c.SendResponse(r, err, err.Error())
		return
	}
	if len(resp.NotFoundInCCHosts) == len(input.Hosts) {
		c.SendResponse(r, fmt.Errorf("all machines failed to query cmdb information"), resp)
		return
	}
	c.SendResponse(r, err, resp)
}

// ImportHostResp 导入主机参数
type ImportHostResp struct {
	GetDiskInfoJobErrMsg string            `json:"get_disk_job_errmsg"`
	SearchDiskErrInfo    map[string]string `json:"search_disk_err_info"`
	NotFoundInCCHosts    []string          `json:"not_found_in_cc_hosts"`
}

func (p ImportMachParam) transParamToBytes() (lableJson json.RawMessage, err error) {
	return marshalLables(p.Labels)
}

// marshalLables TODO
func marshalLables(labels []string) (json.RawMessage, error) {
	if len(labels) == 0 {
		return []byte("[]"), nil
	}
	lableJson, err := json.Marshal(labels)
	if err != nil {
		logger.Error(fmt.Sprintf("ConverLableToJsonStr Failed,Error:%s", err.Error()))
		return []byte("[]"), err
	}
	return lableJson, err
}

func (p ImportMachParam) getJobIpList() (ipList []bk.IPList) {
	return lo.Map(p.Hosts, func(host HostBase, _ int) bk.IPList {
		return bk.IPList{
			IP:        host.Ip,
			BkCloudID: host.BkCloudId,
		}
	})
}

// Doimport do import
func Doimport(param ImportMachParam, requestId string) (resp *ImportHostResp, err error) {
	var ccHostsInfo []*cc.Host
	var derr error
	var diskResp bk.GetDiskResp
	var notFoundHosts []string
	var bkHostIds []int
	var elems []model.TbRpDetail
	resp = &ImportHostResp{}
	targetHosts := lo.Uniq(param.getIps())
	if len(targetHosts) == 0 {
		return resp, nil
	}
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
		bkHostIds = append(bkHostIds, h.BKHostId)
		diskDetails := []yunti.CvmDataDisk{}
		if v, ok := cvmInfoMap[h.InnerIP]; ok {
			el.DramCap = v.Memory * 1000
			for _, disk := range v.DatadiskList {
				logger.Info("get disk info from yunti %v", disk.DiskId)
			}
			diskDetails = v.DatadiskList
		}
		el.SetMore(h.InnerIP, diskResp.IpLogContentMap, diskDetails)
		elems = append(elems, el)
	}
	if err = model.DB.Self.Table(model.TbRpDetailName()).Create(elems).Error; err != nil {
		logger.Error("failed to save resource: %s", err.Error())
		return resp, err
	}
	task.SyncRsGseAgentStatusChan <- bkHostIds
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
	return buildTbRpItem(h, p.ForBiz, p.BkBizId, bkCloudId, p.RsType, label, p.Operator)
}

func buildTbRpItem(h *cc.Host, forBizId, bkbizId, bkCloudId int, rsType string, label []byte,
	operator string) model.TbRpDetail {
	osType := h.BkOsType
	if lo.IsEmpty(osType) {
		osType = bk.OsLinux
	}
	return model.TbRpDetail{
		DedicatedBiz:          forBizId,
		RsType:                dealEmptyRs(rsType),
		BkCloudID:             bkCloudId,
		BkBizId:               bkbizId,
		AssetID:               h.AssetID,
		BkHostID:              h.BKHostId,
		IP:                    h.InnerIP,
		Labels:                label,
		DeviceClass:           h.DeviceClass,
		DramCap:               h.BkMem,
		CPUNum:                h.BkCpu,
		City:                  h.IdcCityName,
		CityID:                h.IdcCityId,
		SubZone:               h.SZone,
		SubZoneID:             h.SZoneID,
		RackID:                cleanStr(h.Equipment),
		SvrTypeName:           h.SvrTypeName,
		Status:                model.Unused,
		NetDeviceID:           util.TransInnerSwitchIpAsNetDeviceId(h.InnerSwitchIp),
		StorageDevice:         []byte("{}"),
		TotalStorageCap:       h.BkDisk,
		BkAgentId:             h.BkAgentId,
		AgentStatusCode:       bk.GseAlive,
		AgentStatusUpdateTime: time.Now(),
		OsType:                model.ConvertOsTypeToHuman(osType),
		OsBit:                 h.BkOsBit,
		OsVerion:              h.BkOsVersion,
		OsName:                util.CleanOsName(h.OSName),
		Operator:              operator,
		UpdateTime:            time.Now(),
		CreateTime:            time.Now(),
	}
}

func dealEmptyRs(rsType string) string {
	if lo.IsEmpty(rsType) {
		return model.PUBLIC_RESOURCE_DBTYEP
	}
	return rsType
}

func cleanStr(v string) string {
	return strings.ReplaceAll(strings.TrimSpace(v), "\"", "")
}

// ImportMachineWithDiffInfoParam 导入主机信息
type ImportMachineWithDiffInfoParam struct {
	Hosts []HostInfo `json:"hosts" binding:"required,dive,required"`
	apply.ActionInfo
}

// HostInfo 主机信息
type HostInfo struct {
	Ip        string `json:"ip"  binding:"required,ip"`
	HostId    int    `json:"host_id" binding:"required"`
	BkBizId   int    `json:"bk_biz_id"  binding:"required,number"`
	BkCloudId int    `json:"bk_cloud_id"`
	// 机器导入的专属业务id
	ForBiz int    `json:"for_biz"`
	RsType string `json:"resource_type"`
	// 机器所在业务的 bk_biz_id
	Labels []string `json:"labels"`
}

// ImportMachineWithDiffInfo 导入主机信息
// nolint
func (c *MachineResourceHandler) ImportMachineWithDiffInfo(r *rf.Context) {
	var input ImportMachineWithDiffInfoParam
	if err := c.Prepare(r, &input); err != nil {
		logger.Error(fmt.Sprintf("Preare Error %s", err.Error()))
		return
	}
	hostMap := make(map[int]HostInfo)
	hostsGroupbyBkBizId := make(map[int][]HostInfo)
	for _, v := range input.Hosts {
		hostMap[v.HostId] = v
		hostsGroupbyBkBizId[v.BkBizId] = append(hostsGroupbyBkBizId[v.BkBizId], v)
	}
	var elems []model.TbRpDetail
	var bkHostIds []int
	for bkBizId, hostList := range hostsGroupbyBkBizId {
		var ccHostsInfo []*cc.Host
		var diskResp bk.GetDiskResp
		var notFoundHosts []string
		var err error
		targetHosts := getIpList(hostList)
		ccHostsInfo, notFoundHosts, err = bk.BatchQueryHostsInfo(bkBizId, targetHosts)
		if err != nil {
			logger.Error("query cc info from cmdb failed %s", err.Error())
			c.SendResponse(r, err, err)
			return
		}
		hostOsMap := lo.SliceToMap(ccHostsInfo, func(item *cc.Host) (string, string) {
			return item.InnerIP, model.ConvertOsTypeToHuman(item.BkOsType)
		})

		diskResp, err = bk.GetDiskInfo(buildJobIpList(hostList), bkBizId, hostOsMap)
		if err != nil {
			logger.Error("get disk info failed %s", err.Error())
			c.SendResponse(r, err, err)
			return
		}
		hostsMap := lo.SliceToMap(targetHosts, func(item string) (string, struct{}) { return item, struct{}{} })
		for _, emptyhost := range notFoundHosts {
			delete(hostsMap, emptyhost)
		}
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
			hostInfo, ok := hostMap[h.BKHostId]
			if !ok {
				logger.Error("host not found in input hosts %s", h.InnerIP)
				continue
			}
			jsonRaw, err := marshalLables(hostInfo.Labels)
			if err != nil {
				logger.Error("marshal labels failed %s", err.Error())
				c.SendResponse(r, err, err)
				return
			}
			el := buildTbRpItem(h, hostInfo.ForBiz, hostInfo.BkBizId, hostInfo.BkCloudId, hostInfo.RsType, jsonRaw,
				input.Operator)
			bkHostIds = append(bkHostIds, h.BKHostId)
			diskDetailInfo := []yunti.CvmDataDisk{}
			if v, ok := cvmInfoMap[h.InnerIP]; ok {
				el.DramCap = v.Memory * 1000
				diskDetailInfo = v.DatadiskList
			}
			el.SetMore(h.InnerIP, diskResp.IpLogContentMap, diskDetailInfo)
			elems = append(elems, el)
		}
	}
	if err := model.DB.Self.Table(model.TbRpDetailName()).Create(elems).Error; err != nil {
		c.SendResponse(r, err, err)
	}
	task.SyncRsGseAgentStatusChan <- bkHostIds
	c.SendResponse(r, nil, "success")
}

func getIpList(ss []HostInfo) (ips []string) {
	for _, v := range ss {
		ips = append(ips, v.Ip)
	}
	return
}
func buildJobIpList(ss []HostInfo) (ipList []bk.IPList) {
	for _, v := range ss {
		ipList = append(ipList, bk.IPList{
			IP:        v.Ip,
			BkCloudID: v.BkCloudId,
		})
	}
	return
}
