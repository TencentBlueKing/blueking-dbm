/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package bk

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"maps"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
)

const (
	// SSD disk type
	SSD = "SSD"
)

// ShellResCollection Liunx os info
type ShellResCollection struct {
	Cpu      int        `json:"cpu"`
	Mem      int        `json:"mem"` // MB
	TxRegion string     `json:"region"`
	TxZone   string     `json:"zone"`
	Disk     []DiskInfo `json:"disk"`
}

// PowerShellResCollection window os info
type PowerShellResCollection struct {
	Cpu      int                `json:"cpu"`
	Mem      int                `json:"mem"` // MB
	TxRegion string             `json:"region"`
	TxZone   string             `json:"zone"`
	Disk     []WindowDiskDetail `json:"disk"`
}

// DiskInfo TODO
type DiskInfo struct {
	// 挂载点
	MountPoint string `json:"mount_point"`
	DiskDetail
}

// WindowDiskDetail windows 磁盘明细
type WindowDiskDetail struct {
	DriveLetter string `json:"DriveLetter"`
	TotalSize   uint64 `json:"TotalSize"`
	FileSystem  string `json:"FileSystem"`
}

func diskFormartTrans(windisks []WindowDiskDetail) (commDisk []DiskInfo) {
	for _, v := range windisks {
		commDisk = append(commDisk, DiskInfo{
			MountPoint: v.DriveLetter,
			DiskDetail: DiskDetail{
				Size:     int(v.TotalSize / 1024 / 1024 / 1024),
				FileType: v.FileSystem,
			},
		})
	}
	return
}

// DiskDetail TODO
type DiskDetail struct {
	Size int `json:"size"`
	// 磁盘格式化类型 ext4,xfs
	FileType string `json:"file_type"`
	// 磁盘类型,是SSD还是非ssd
	DiskType string `json:"disk_type"`
	DiskId   string `json:"disk_id"`
}

// GetDiskInfoShellContent TODO
var GetDiskInfoShellContent []byte

// GetWinDiskInfoShellContent TODO
var GetWinDiskInfoShellContent []byte

func init() {
	var err error
	GetDiskInfoShellContent, err = GetDiskInfoScript.ReadFile(LiunxDiskScriptName)
	if err != nil {
		logger.Fatal("read get disk info shell content  failed %s", err.Error())
	}
	GetWinDiskInfoShellContent, err = GetWinDiskScrip.ReadFile(WinDiskScriptName)
	if err != nil {
		logger.Fatal("read get disk info shell content  failed %s", err.Error())
	}
}

// GetAllDiskIds TODO
func GetAllDiskIds(c []DiskInfo) (diskIds []string) {
	for _, v := range c {
		if cmutil.IsNotEmpty(v.DiskId) {
			diskIds = append(diskIds, v.DiskId)
		}
	}
	return
}

// MarshalDisk TODO
func MarshalDisk(c []DiskInfo) (result string, err error) {
	var b []byte
	t := make(map[string]DiskDetail)
	for idx, v := range c {
		if cmutil.IsEmpty(v.MountPoint) {
			v.MountPoint = fmt.Sprintf("NOMOUNT%d", idx)
		}
		t[v.MountPoint] = v.DiskDetail
	}
	if b, err = json.Marshal(t); err != nil {
		logger.Error("marshal disk info failed ")
		return "{}", err
	}
	return string(b), nil
}

// SetDiskType TODO
func SetDiskType(elems []DiskInfo, t string) (ds []DiskInfo) {
	for _, v := range elems {
		d := v
		d.DiskType = t
		ds = append(ds, d)
	}
	return ds
}

// GetDiskResp TODO
type GetDiskResp struct {
	IpLogContentMap map[string]*ShellResCollection
	IpFailedLogMap  map[string]string
}

// GetDiskInfo TODO
func GetDiskInfo(hosts []IPList, bk_biz_id int, hostOsMap map[string]string) (resp GetDiskResp, err error) {
	ipListOsMap := make(map[string][]IPList)
	for _, host := range hosts {
		if os_type, ok := hostOsMap[host.IP]; ok {
			ipListOsMap[os_type] = append(ipListOsMap[os_type], host)
		} else {
			logger.Warn("没有获取到%s的操作系统类型", host.IP)
			// 默认当做Liunx处理
			ipListOsMap[OsLinux] = append(ipListOsMap[os_type], host)
		}
	}
	ipLogContentMap := make(map[string]*ShellResCollection)
	ipFailedLogMap := make(map[string]string)
	for os_type, ipList := range ipListOsMap {
		if len(ipList) <= 0 {
			continue
		}
		switch os_type {
		case OsWindows:
			ipFailedLogMapWin, ipLogs, err := GetWindowsDiskInfo(ipList, bk_biz_id)
			if err != nil {
				return GetDiskResp{}, err
			}
			maps.Copy(ipFailedLogMap, ipFailedLogMapWin)
			for _, d := range ipLogs.ScriptTaskLogs {
				var dl PowerShellResCollection
				if err = json.Unmarshal([]byte(d.LogContent), &dl); err != nil {
					logger.Error("unmarshal log content failed %s", err.Error())
					continue
				}
				ipLogContentMap[d.Ip] = &ShellResCollection{
					Cpu:  dl.Cpu,
					Mem:  dl.Mem,
					Disk: diskFormartTrans(dl.Disk),
				}
			}
		case OsLinux:
			ipFailedLogMapLiunx, ipLogs, err := GetLiunxDiskInfo(ipList, bk_biz_id)
			if err != nil {
				return GetDiskResp{}, err
			}
			maps.Copy(ipFailedLogMap, ipFailedLogMapLiunx)
			for _, d := range ipLogs.ScriptTaskLogs {
				var dl ShellResCollection
				if err = json.Unmarshal([]byte(d.LogContent), &dl); err != nil {
					logger.Error("unmarshal log content failed %s", err.Error())
					continue
				}
				ipLogContentMap[d.Ip] = &dl
			}
		}
	}
	resp.IpFailedLogMap = ipFailedLogMap
	resp.IpLogContentMap = ipLogContentMap
	return resp, nil
}

// GetLiunxDiskInfo 获取liunx系统的磁盘信息
func GetLiunxDiskInfo(hosts []IPList, bk_biz_id int) (ipFailedLogMap map[string]string,
	ipLogs BatchGetJobInstanceIpLogRpData, err error) {
	param := &FastExecuteScriptParam{
		BkBizID:        bk_biz_id,
		ScriptContent:  base64.StdEncoding.EncodeToString(GetDiskInfoShellContent),
		ScriptTimeout:  300,
		ScriptLanguage: 1,
		AccountAlias:   "root",
		TargetServer: TargetServer{
			IPList: hosts,
		},
	}
	return getDiskInfoBase(hosts, bk_biz_id, param)
}

// GetWindowsDiskInfo 获取window 机器磁盘信息
func GetWindowsDiskInfo(hosts []IPList, bk_biz_id int) (ipFailedLogMap map[string]string,
	ipLogs BatchGetJobInstanceIpLogRpData, err error) {
	param := &FastExecuteScriptParam{
		BkBizID:        bk_biz_id,
		ScriptContent:  base64.StdEncoding.EncodeToString(GetWinDiskInfoShellContent),
		ScriptTimeout:  300,
		ScriptLanguage: 5,
		AccountAlias:   "system",
		TargetServer: TargetServer{
			IPList: hosts,
		},
	}
	return getDiskInfoBase(hosts, bk_biz_id, param)
}

func getDiskInfoBase(hosts []IPList, bk_biz_id int, param *FastExecuteScriptParam) (ipFailedLogMap map[string]string,
	ipLogs BatchGetJobInstanceIpLogRpData, err error) {
	jober := JobV3{
		Client: EsbClient,
	}
	job, err := jober.ExecuteJob(param)
	if err != nil {
		logger.Error("call execute job failed %s", err.Error())
		return nil, BatchGetJobInstanceIpLogRpData{}, err
	}
	// 查询任务
	var errCnt int
	var jobStatus GetJobInstanceStatusRpData
	for i := 0; i < 100; i++ {
		jobStatus, err = jober.GetJobStatus(&GetJobInstanceStatusParam{
			BKBizId:       bk_biz_id,
			JobInstanceID: job.JobInstanceID,
		})
		if err != nil {
			logger.Error("query job %d status failed %s", job.JobInstanceID, err.Error())
			errCnt++
		}
		if jobStatus.Finished {
			break
		}
		if errCnt > 10 {
			return nil, BatchGetJobInstanceIpLogRpData{}, fmt.Errorf("more than 10 errors when query job %d,some err: %s",
				job.JobInstanceID,
				err.Error())
		}
		time.Sleep(1 * time.Second)
	}
	// 再查询一遍状态
	jobStatus, err = jober.GetJobStatus(&GetJobInstanceStatusParam{
		BKBizId:       bk_biz_id,
		JobInstanceID: job.JobInstanceID,
	})
	if err != nil {
		logger.Error("query job %d status failed %s", job.JobInstanceID, err.Error())
		return nil, BatchGetJobInstanceIpLogRpData{}, err
	}
	ipFailedLogMap = analyzeJobIpFailedLog(jobStatus)
	// 查询执行输出
	// var ipLogs BatchGetJobInstanceIpLogRpData
	ipLogs, err = jober.BatchGetJobInstanceIpLog(&BatchGetJobInstanceIpLogParam{
		BKBizId:        bk_biz_id,
		JobInstanceID:  job.JobInstanceID,
		StepInstanceID: job.StepInstanceID,
		IPList:         hosts,
	})
	return ipFailedLogMap, ipLogs, err
}

func analyzeJobIpFailedLog(jobStatus GetJobInstanceStatusRpData) map[string]string {
	ipFailedLogMap := make(map[string]string)
	for _, stepInstance := range jobStatus.StepInstanceList {
		for _, step_ip_result := range stepInstance.StepIpResultList {
			switch step_ip_result.Status {
			case 1:
				ipFailedLogMap[step_ip_result.IP] += "Agent异常\n"
			case 12:
				ipFailedLogMap[step_ip_result.IP] += "任务下发失败\n"
			case 403:
				ipFailedLogMap[step_ip_result.IP] += "任务强制终止成功\n"
			case 404:
				ipFailedLogMap[step_ip_result.IP] += "任务强制终止失败\n"
			case 11:
				ipFailedLogMap[step_ip_result.IP] += "执行失败;\n"
			default:
				continue
			}
		}
	}
	return ipFailedLogMap
}
