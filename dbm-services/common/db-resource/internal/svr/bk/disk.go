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
	"regexp"
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

// extractFirstJSONObject 从字符串中提取第一个完整的 JSON 对象
// 处理嵌套大括号和多个 JSON 对象连在一起的情况
func extractFirstJSONObject(content string) string {
	logger.Debug("extractFirstJSONObject: 开始提取 JSON，原始内容长度: %d", len(content))
	if len(content) == 0 {
		logger.Warn("extractFirstJSONObject: 内容为空")
		return ""
	}

	start := -1
	depth := 0
	inString := false
	escapeNext := false

	for i, char := range content {
		if escapeNext {
			escapeNext = false
			continue
		}

		switch char {
		case '\\':
			if inString {
				escapeNext = true
			}
		case '"':
			inString = !inString
		case '{':
			if !inString {
				if start == -1 {
					start = i
					logger.Debug("extractFirstJSONObject: 找到第一个 '{' 位置: %d", i)
				}
				depth++
				logger.Debug("extractFirstJSONObject: 深度增加，当前深度: %d", depth)
			}
		case '}':
			if !inString {
				depth--
				logger.Debug("extractFirstJSONObject: 深度减少，当前深度: %d", depth)
				if depth == 0 && start != -1 {
					result := content[start : i+1]
					logger.Info("extractFirstJSONObject: 成功提取 JSON，起始位置: %d, 结束位置: %d, 长度: %d",
						start, i+1, len(result))
					return result
				}
			}
		}
	}

	// 如果没有找到完整的 JSON 对象，尝试使用正则表达式作为后备方案
	logger.Warn("extractFirstJSONObject: 使用深度计数器未找到完整 JSON，尝试正则表达式后备方案")
	logger.Debug("extractFirstJSONObject: 最终状态 - start: %d, depth: %d, inString: %v", start, depth, inString)
	jsonRe := regexp.MustCompile(`\{[^{}]*\}`)
	if match := jsonRe.FindString(content); match != "" {
		logger.Info("extractFirstJSONObject: 使用正则表达式提取到 JSON，长度: %d", len(match))
		return match
	}

	preview := content
	if len(content) > 100 {
		preview = content[:100] + "..."
	}
	logger.Error("extractFirstJSONObject: 未能提取到任何 JSON 对象，原始内容前100字符: %s", preview)
	return ""
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
	logger.Info("GetDiskInfo 开始处理，主机数量: %d, bk_biz_id: %d", len(hosts), bk_biz_id)
	ipListOsMap := make(map[string][]IPList)
	for _, host := range hosts {
		if os_type, ok := hostOsMap[host.IP]; ok {
			ipListOsMap[os_type] = append(ipListOsMap[os_type], host)
			logger.Debug("主机 %s 操作系统类型: %s", host.IP, os_type)
		} else {
			logger.Warn("没有获取到%s的操作系统类型，默认当做Linux处理", host.IP)
			// 默认当做Linux处理
			ipListOsMap[OsLinux] = append(ipListOsMap[OsLinux], host)
		}
	}
	logger.Info("按操作系统类型分组完成 - Windows: %d, Linux: %d",
		len(ipListOsMap[OsWindows]), len(ipListOsMap[OsLinux]))
	ipLogContentMap := make(map[string]*ShellResCollection)
	ipFailedLogMap := make(map[string]string)
	for os_type, ipList := range ipListOsMap {
		if len(ipList) == 0 {
			continue
		}
		switch os_type {
		case OsWindows:
			ipFailedLogMapWin, ipLogs, err := GetWindowsDiskInfo(ipList, bk_biz_id)
			if err != nil {
				logger.Error("GetWindowsDiskInfo failed: %s", err.Error())
				return GetDiskResp{}, err
			}
			maps.Copy(ipFailedLogMap, ipFailedLogMapWin)
			logger.Info("开始处理 Windows 系统磁盘信息，IP 数量: %d", len(ipLogs.ScriptTaskLogs))
			for _, d := range ipLogs.ScriptTaskLogs {
				var dl PowerShellResCollection
				jsonBody := d.LogContent
				logger.Info("%s Windows shell grab json body，长度: %d, 内容: %s", d.Ip, len(jsonBody), jsonBody)
				if err = json.Unmarshal([]byte(jsonBody), &dl); err != nil {
					logger.Error("%s unmarshal Windows log content failed: %s, 原始内容: %s",
						d.Ip, err.Error(), jsonBody)
					continue
				}
				logger.Info("%s Windows 解析成功 - CPU: %d, Mem: %d MB, Disk数量: %d",
					d.Ip, dl.Cpu, dl.Mem, len(dl.Disk))
				ipLogContentMap[d.Ip] = &ShellResCollection{
					Cpu:  dl.Cpu,
					Mem:  dl.Mem,
					Disk: diskFormartTrans(dl.Disk),
				}
			}
		case OsLinux:
			ipFailedLogMapLiunx, ipLogs, err := GetLiunxDiskInfo(ipList, bk_biz_id)
			if err != nil {
				logger.Error("GetLiunxDiskInfo failed: %s", err.Error())
				return GetDiskResp{}, err
			}
			maps.Copy(ipFailedLogMap, ipFailedLogMapLiunx)
			logger.Info("开始处理 Linux 系统磁盘信息，IP 数量: %d", len(ipLogs.ScriptTaskLogs))
			for _, d := range ipLogs.ScriptTaskLogs {
				var dl ShellResCollection
				preview := d.LogContent
				if len(d.LogContent) > 200 {
					preview = d.LogContent[:200] + "..."
				}
				logger.Debug("%s 原始日志内容长度: %d, 内容预览: %s", d.Ip, len(d.LogContent), preview)
				jsonBody := extractFirstJSONObject(d.LogContent)
				if jsonBody == "" {
					logger.Error("%s failed to extract json from log content，原始内容长度: %d, 内容: %s",
						d.Ip, len(d.LogContent), d.LogContent)
					continue
				}
				logger.Info("%s Linux shell grab json body，提取长度: %d, 内容: %s",
					d.Ip, len(jsonBody), jsonBody)
				if err = json.Unmarshal([]byte(jsonBody), &dl); err != nil {
					logger.Error("%s unmarshal Linux log content failed: %s, 提取的 JSON: %s, 原始内容: %s",
						d.Ip, err.Error(), jsonBody, d.LogContent)
					continue
				}
				logger.Info("%s Linux 解析成功 - CPU: %d, Mem: %d MB, Region: %s, Zone: %s, Disk数量: %d",
					d.Ip, dl.Cpu, dl.Mem, dl.TxRegion, dl.TxZone, len(dl.Disk))
				ipLogContentMap[d.Ip] = &dl
			}
		}
	}
	resp.IpFailedLogMap = ipFailedLogMap
	resp.IpLogContentMap = ipLogContentMap
	logger.Info("GetDiskInfo 处理完成 - 成功解析: %d 个IP, 失败: %d 个IP",
		len(ipLogContentMap), len(ipFailedLogMap))
	if len(ipFailedLogMap) > 0 {
		ips := make([]string, 0, len(ipFailedLogMap))
		for ip := range ipFailedLogMap {
			ips = append(ips, ip)
		}
		logger.Warn("GetDiskInfo 失败的IP列表: %v", ips)
	}
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
		Client: BkJobClient,
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
			BkScopeType:   "biz",
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
		BkScopeType:   "biz",
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
