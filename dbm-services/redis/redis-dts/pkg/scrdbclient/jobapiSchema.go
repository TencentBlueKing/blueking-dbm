// Package scrdbclient ..
package scrdbclient

import (
	"dbm-services/redis/redis-dts/util"

	"github.com/spf13/viper"
)

// IPItem bk_cloud_id and ip
type IPItem struct {
	BkCloudID int    `json:"bk_cloud_id"`
	IP        string `json:"ip"`
}

// FastExecScriptReq jobapi fast_execute_script request
type FastExecScriptReq struct {
	IPList         []IPItem `json:"ip_list"`
	ScriptLanguage int      `json:"script_language"`
	ScriptContent  string   `json:"script_content"`
	Account        string   `json:"account"`
	Timeout        int      `json:"timeout"`
}

// IsLocalScript 是否是本地命令
func (req *FastExecScriptReq) IsLocalScript() (ret bool, err error) {
	var localIP string
	localIP, err = util.GetLocalIP()
	if err != nil {
		return
	}
	for _, ipitem := range req.IPList {
		if ipitem.IP != localIP {
			return false, nil
		}
		if ipitem.BkCloudID != viper.GetInt("bkDbm.bk_cloud_id") {
			return false, nil
		}
	}
	return true, nil
}

// FastExecScriptResp jobapi  get_job_instance_status response
type FastExecScriptResp struct {
	JobInstanceItem
	JobInstanceName string `json:"job_instance_name"`
}

// JobInstanceItem ..
type JobInstanceItem struct {
	JobInstanceID  int64 `json:"job_instance_id"`
	StepInstanceID int64 `json:"step_instance_id"`
}

// GetJobInstanceStatusReq jobapi  get_job_instance_status request
type GetJobInstanceStatusReq struct {
	JobInstanceItem
}

// GetJobInstanceStatusResp jobapi  get_job_instance_status response
type GetJobInstanceStatusResp struct {
	JobInstance struct {
		BkBizID       int    `json:"bk_biz_id"`
		JobInstanceID int64  `json:"job_instance_id"`
		Name          string `json:"name"`
		BkScopeType   string `json:"bk_scope_type"`
		StartTime     int64  `json:"start_time"`
		BkScopeID     string `json:"bk_scope_id"`
		CreateTime    int64  `json:"create_time"`
		Status        int    `json:"status"`
		EndTime       int64  `json:"end_time"`
		TotalTime     int    `json:"total_time"`
	} `json:"job_instance"`
	Finished         bool `json:"finished"`
	StepInstanceList []struct {
		Status           int    `json:"status"`
		TotalTime        int    `json:"total_time"`
		Name             string `json:"name"`
		StartTime        int64  `json:"start_time"`
		StepInstanceID   int64  `json:"step_instance_id"`
		StepIPResultList []struct {
			Status    int    `json:"status"`
			TotalTime int    `json:"total_time"`
			IP        string `json:"ip"`
			StartTime int64  `json:"start_time"`
			BkHostID  int    `json:"bk_host_id"`
			ExitCode  int    `json:"exit_code"`
			BkCloudID int    `json:"bk_cloud_id"`
			Tag       string `json:"tag"`
			EndTime   int64  `json:"end_time"`
			ErrorCode int    `json:"error_code"`
		} `json:"step_ip_result_list"`
		CreateTime   int64 `json:"create_time"`
		EndTime      int64 `json:"end_time"`
		ExecuteCount int   `json:"execute_count"`
		Type         int   `json:"type"`
	} `json:"step_instance_list"`
}

// BatchGetJobInstanceIpLogReq  jobapi batch_get_job_instance_ip_log request
type BatchGetJobInstanceIpLogReq struct {
	JobInstanceItem
	IPList []IPItem `json:"ip_list"`
}

// ScriptTaskLogItem jobapi et_job_instance_ip_log response item
type ScriptTaskLogItem struct {
	HostID     int         `json:"host_id"`
	Ipv6       interface{} `json:"ipv6"`
	LogContent string      `json:"log_content"`
	BkCloudID  int         `json:"bk_cloud_id"`
	IP         string      `json:"ip"`
}

// BatchGetJobInstanceIpLogResp  jobapi batch_get_job_instance_ip_log response
type BatchGetJobInstanceIpLogResp struct {
	JobInstanceID  int64               `json:"job_instance_id"`
	FileTaskLogs   interface{}         `json:"file_task_logs"`
	ScriptTaskLogs []ScriptTaskLogItem `json:"script_task_logs"`
	StepInstanceID int64               `json:"step_instance_id"`
	LogType        int                 `json:"log_type"`
}

// ToBatchScriptLogList 转换为BatchScriptLogList
func (rsp *BatchGetJobInstanceIpLogResp) ToBatchScriptLogList() (ret []BatchScriptLogItem) {
	for _, item := range rsp.ScriptTaskLogs {
		ret = append(ret, BatchScriptLogItem{
			IPItem: IPItem{
				BkCloudID: item.BkCloudID,
				IP:        item.IP,
			},
			LogContent: item.LogContent,
		})
	}
	return
}

// BatchScriptLogItem 脚本执行结果日志
type BatchScriptLogItem struct {
	IPItem
	LogContent string `json:"log_content"`
}

// TransferFileSourceItem jobapi  transfer_file file_source
type TransferFileSourceItem struct {
	BkCloudID int      `json:"bk_cloud_id"`
	IP        string   `json:"ip"`
	Account   string   `json:"account"`
	FileList  []string `json:"file_list"`
}

// TransferFileReq jobapi transfer_file request
type TransferFileReq struct {
	SourceList    []TransferFileSourceItem `json:"source_list"`
	TargetAccount string                   `json:"target_account"`
	TargetDir     string                   `json:"target_dir"`
	TargetIPList  []IPItem                 `json:"target_ip_list"`
	Timeout       int                      `json:"timeout"`
}

// IsLocalCopy 是否源和目标都是本机
func (req *TransferFileReq) IsLocalCopy() (ret bool, err error) {
	var localIP string
	localIP, err = util.GetLocalIP()
	if err != nil {
		return
	}
	for _, ipitem := range req.TargetIPList {
		if ipitem.IP != localIP {
			return false, nil
		}
		if ipitem.BkCloudID != viper.GetInt("bkDbm.bk_cloud_id") {
			return false, nil
		}
	}
	for _, sitem := range req.SourceList {
		if sitem.IP != localIP {
			return false, nil
		}
		if sitem.BkCloudID != viper.GetInt("bkDbm.bk_cloud_id") {
			return false, nil
		}
	}
	return true, nil
}

// IsLocalTarget 是否目标是本机
func (req *TransferFileReq) IsLocalTarget() (ret bool, err error) {
	var localIP string
	localIP, err = util.GetLocalIP()
	if err != nil {
		return
	}
	for _, ipitem := range req.TargetIPList {
		if ipitem.IP != localIP {
			return false, nil
		}
		if ipitem.BkCloudID != viper.GetInt("bkDbm.bk_cloud_id") {
			return false, nil
		}
	}
	return true, nil
}
