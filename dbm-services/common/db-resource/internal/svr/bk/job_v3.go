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
	"embed"
	"encoding/json"
	"net/http"
	"path"

	"dbm-services/common/go-pubpkg/cc.v3"
	"dbm-services/common/go-pubpkg/logger"
)

// Jober TODO
type Jober interface {
	Execute()
}

// LiunxDiskScriptName   获取Liunx磁盘脚本名称
var LiunxDiskScriptName = "get_block_info.sh"

// WinDiskScriptName  获取windows磁盘脚本名称
var WinDiskScriptName = "get_win_disk.ps1"

// GetDiskInfoScript 获取Liunx磁盘脚本
//
//go:embed get_block_info.sh
var GetDiskInfoScript embed.FS

// GetWinDiskScrip 获取windows磁盘脚本
//
//go:embed get_win_disk.ps1
var GetWinDiskScrip embed.FS

const (
	// ESB_PREFIX TODO
	ESB_PREFIX = "/api/c/compapi/v2/jobv3/"
	// 快速执行脚本
	fast_execute_script = "fast_execute_script/"
	// 查询作业执行状态
	get_job_status = "get_job_instance_status/"
	// 根据作业实例ID查询作业执行日志
	// get_job_instance_ip_log = "get_job_instance_ip_log/"
	// 根据ip列表批量查询作业执行日志
	batch_get_job_instance_ip_log = "batch_get_job_instance_ip_log/"
)

// FastExecuteScriptParam TODO
type FastExecuteScriptParam struct {
	BkBizID          int          `json:"bk_biz_id"`
	ScriptID         int          `json:"script_id,omitempty"`
	ScriptContent    string       `json:"script_content"`
	ScriptParam      string       `json:"script_param,omitempty"`
	ScriptTimeout    int          `json:"script_timeout,omitempty"`
	AccountAlias     string       `json:"account_alias"`
	IsParamSensitive int          `json:"is_param_sensitive,omitempty"`
	ScriptLanguage   int          `json:"script_language"`
	TargetServer     TargetServer `json:"target_server"`
}

// FastExecuteScriptRpData TODO
type FastExecuteScriptRpData struct {
	JobInstanceName string `json:"job_instance_name"`
	JobInstanceID   int64  `json:"job_instance_id"`
	StepInstanceID  int64  `json:"step_instance_id"`
}

// TargetServer TODO
type TargetServer struct {
	DynamicGroupIDList []string       `json:"dynamic_group_id_list,omitempty"`
	IPList             []IPList       `json:"ip_list"`
	TopoNodeList       []TopoNodeList `json:"topo_node_list,omitempty"`
}

// IPList TODO
type IPList struct {
	BkCloudID int    `json:"bk_cloud_id"`
	IP        string `json:"ip"`
}

// TopoNodeList TODO
type TopoNodeList struct {
	ID       int    `json:"id"`
	NodeType string `json:"node_type"`
}

// BatchGetJobInstanceIpLogParam TODO
type BatchGetJobInstanceIpLogParam struct {
	BKBizId        int      `json:"bk_biz_id"`
	JobInstanceID  int64    `json:"job_instance_id"`
	StepInstanceID int64    `json:"step_instance_id"`
	IPList         []IPList `json:"ip_list"`
}

// BatchGetJobInstanceIpLogRpData TODO
type BatchGetJobInstanceIpLogRpData struct {
	BkCloudID      int             `json:"bk_cloud_id"`
	LogType        int             `json:"log_type"`
	ScriptTaskLogs []ScriptTaskLog `json:"script_task_logs"`
}

// ScriptTaskLog TODO
type ScriptTaskLog struct {
	BkCloudID  int    `json:"bk_cloud_id"`
	Ip         string `json:"ip"`
	LogContent string `json:"log_content"`
}

// GetJobInstanceStatusParam TODO
type GetJobInstanceStatusParam struct {
	BKBizId       int   `json:"bk_biz_id"`
	JobInstanceID int64 `json:"job_instance_id"`
	// 是否返回每个ip上的任务详情，对应返回结果中的step_ip_result_list。默认值为false。
	ReturnIpResult bool `json:"return_ip_result"`
}

// GetJobInstanceStatusRpData TODO
type GetJobInstanceStatusRpData struct {
	Finished         bool           `json:"finished"`
	JobInstance      JobInstance    `json:"job_instance"`
	StepInstanceList []StepInstance `json:"step_instance_list"`
}

// JobInstance TODO
type JobInstance struct {
	Name          string `json:"name"`
	Status        int    `json:"status"`
	CreateTime    int64  `json:"create_time"`
	StartTime     int64  `json:"start_time"`
	EndTime       int64  `json:"end_time"`
	TotalTime     int64  `json:"total_time"`
	BkBizID       int    `json:"bk_biz_id"`
	JobInstanceID int    `json:"job_instance_id"`
}

// StepInstance TODO
type StepInstance struct {
	StepInstanceID   int            `json:"step_instance_id"`
	Type             int            `json:"type"`
	Name             string         `json:"name"`
	Status           int            `json:"status"`
	CreateTime       int64          `json:"create_time"`
	StartTime        int64          `json:"start_time"`
	EndTime          int64          `json:"end_time"`
	TotalTime        int64          `json:"total_time"`
	RetryCount       int            `json:"execute_count"` // 步骤重试次数
	StepIpResultList []StepIpResult `json:"step_ip_result_list"`
}

// StepIpResult TODO
type StepIpResult struct {
	IP        string `json:"ip"`
	BkCloudID int    `json:"bk_cloud_id"`
	// 作业执行状态:1.Agent异常; 5.等待执行; 7.正在执行; 9.执行成功; 11.执行失败; 12.任务下发失败; 403.任务强制终止成功; 404.任务强制终止失败
	Status    int `json:"status"`
	ExitCode  int `json:"exit_code"`
	TotalTime int `json:"total_time"`
}

// JobV3 TODO
type JobV3 struct {
	Client *cc.Client
}

// ExecuteJob TODO
func (g *JobV3) ExecuteJob(param *FastExecuteScriptParam) (data FastExecuteScriptRpData, err error) {
	logger.Info("will execute job at %v", param.TargetServer.IPList)
	resp, err := g.Client.Do(http.MethodPost, g.get_fast_execute_script_url(), param)
	if err != nil {
		logger.Error("1 call fast_execute_script failed %s", err.Error())
		g.track(resp)
		return FastExecuteScriptRpData{}, err
	}
	if err = json.Unmarshal(resp.Data, &data); err != nil {
		logger.Error("unmarshal respone data  failed %s,respone message:%s,code:%d", err.Error(), resp.Message, resp.Code)
		return
	}
	return
}

func (g *JobV3) track(resp *cc.Response) {
	if resp != nil {
		logger.Error("track: request id: %s,respone message:%s,code:%d", resp.RequestId, resp.Message, resp.Code)
	}
}

// GetJobStatus TODO
func (g *JobV3) GetJobStatus(param *GetJobInstanceStatusParam) (data GetJobInstanceStatusRpData, err error) {
	resp, err := g.Client.Do(http.MethodPost, g.get_job_status_url(), param)
	if err != nil {
		logger.Error("1 call get_job_status failed %s", err.Error())
		g.track(resp)
		return GetJobInstanceStatusRpData{}, err
	}
	if err = json.Unmarshal(resp.Data, &data); err != nil {
		logger.Error("unmarshal respone data  failed %s,respone message:%s,code:%d", err.Error(), resp.Message, resp.Code)
		return
	}
	return
}

// BatchGetJobInstanceIpLog TODO
func (g *JobV3) BatchGetJobInstanceIpLog(param *BatchGetJobInstanceIpLogParam) (data BatchGetJobInstanceIpLogRpData,
	err error) {
	resp, err := g.Client.Do(http.MethodPost, g.batch_get_job_instance_ip_log_url(), param)
	if err != nil {
		logger.Error("call batch_get_job_instance_ip_log failed %s", err.Error())
		g.track(resp)
		return BatchGetJobInstanceIpLogRpData{}, err
	}
	if err = json.Unmarshal(resp.Data, &data); err != nil {
		logger.Error("unmarshal respone data  failed %s,respone message:%s,code:%d", err.Error(), resp.Message, resp.Code)
		return
	}
	logger.Info("shell return content %v", data.ScriptTaskLogs)
	return
}

func (g *JobV3) get_fast_execute_script_url() string {
	return path.Join(ESB_PREFIX, fast_execute_script)
}

func (g *JobV3) get_job_status_url() string {
	return path.Join(ESB_PREFIX, get_job_status)
}

// func (g *JobV3) get_job_instance_ip_log_url() string {
// 	return path.Join(ESB_PREFIX, get_job_instance_ip_log)
// }

func (g *JobV3) batch_get_job_instance_ip_log_url() string {
	return path.Join(ESB_PREFIX, batch_get_job_instance_ip_log)
}
