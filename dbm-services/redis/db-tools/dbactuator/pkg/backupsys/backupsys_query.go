package backupsys

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"

	"dbm-services/redis/db-tools/dbactuator/pkg/util"

	"dbm-services/redis/db-tools/dbactuator/mylog"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// QueryReq 备份系统查询请求体
type QueryReq struct {
	Params `json:"params"`
}

// Params 备份系统查询请求参数格式
type Params struct {
	Version     string `json:"version"`
	RequestInfo `json:"request_info"`
}

// RequestInfo 备份系统查询请求信息
type RequestInfo struct {
	BaseInfo   `json:"base_info"`
	DetailInfo `json:"detail_info"`
}

// BaseInfo 密钥信息
type BaseInfo struct {
	SysID  string `json:"sys_id" validate:"required"`
	Key    string `json:"key" validate:"required"`
	Ticket string `json:"ticket"`
}

// DetailInfo 查询备份文件api的请求参数
type DetailInfo struct {
	// 备份源IP即提交备份任务的机器IP
	SourceIP string `json:"source_ip" validate:"required"`
	// 提交备份开始时间 如："2022-12-05 00:00:01"
	BeginDate string `json:"begin_date" validate:"required"`
	//备份结束时间 如："2022-12-06 00:00:53" 与begin_date形成一个时间范围，建议begin_date与end_date形成的时间范围不要超过3天
	EndDate string `json:"end_date" validate:"required"`
	// 文件名 可为空
	FileName string `json:"filename"`
	// 文件名是否支持通配符 默认"0"
	// FileSpWildchar string `json:"file_sp_wildchar"`
}

// QueryResult 备份系统查询结果 单条记录信息 备份系统查询ip特定时间段的备份文件结果记录详情
type QueryResult struct {
	TaskID        string `json:"task_id"`         //任务ID，用于拉取备份文件
	Uptime        string `json:"uptime"`          //备份任务上报时间
	FileLastMtime string `json:"file_last_mtime"` // 文件最后修改时间
	SourceIP      string `json:"source_ip"`       //备份源IP
	Md5           string `json:"md5"`
	Size          string `json:"size"`
	FileTag       string `json:"file_tag"` //文件类型 REDIS_FULL、REDIS_BINLOG
	Status        string `json:"status"`
	FileName      string `json:"file_name"`
	Pod           string `json:"pod"`
	Bkstif        string `json:"bkstif"` // 备份状态信息 'done, success', 'Fail: bad md5' 等
	ExpireTime    string `json:"expire_time"`
	Expired       string `json:"expired"`
}

// QueryResp  查询备份文件的响应内容
type QueryResp struct {
	Code   string        `json:"code"`
	Msg    string        `json:"msg"`
	Detail []QueryResult `json:"detail"`
	Num    int           `json:"num"`
}

// QueryRespAbnormal 备份系统 api: 有结果时 detail 是一个 struct，无结果时 detail=""
// QueryResp 的补充
type QueryRespAbnormal struct {
	Code   string `json:"code"`
	Msg    string `json:"msg"`
	Detail string `json:"detail"`
}

// QueryBackupFileResult 查询备份文件结果是否成功
func (task *QueryResult) QueryBackupFileResult() bool {
	return task.Status == consts.BackupTaskSuccess && task.Expired == consts.FileNotExpired
}

// QueryFile 查询备份文件
func (task *QueryReq) QueryFile(params QueryReq) (*QueryResp, error) {
	err := util.ValidateStruct(params)
	if err != nil {
		mylog.Logger.Error("QueryFile:validate struct failed:%v", err)
		return nil, err
	}
	respBody, err := task.Get(params)
	if err != nil {
		mylog.Logger.Error("QueryFile:query backup sys :%v", err)
		return nil, err
	}
	mylog.Logger.Debug("QueryFile get respBody:%v", respBody)

	var resp QueryResp
	err = json.Unmarshal(respBody, &resp)
	if err != nil {
		respAbn := QueryRespAbnormal{}
		err := json.Unmarshal(respBody, &respAbn)
		if err != nil {
			mylog.Logger.Error("QueryFile:Unmarshal failed:%v", err)
			return nil, err
		}
		resp.Code = respAbn.Code
		resp.Msg = respAbn.Msg

	}
	if resp.Code != "0" && resp.Code == "5" {
		mylog.Logger.Warn("QueryFile: backup sys return resp code: %s,resp msg:%s", resp.Code, resp.Msg)
		mylog.Logger.Warn("params:%v", params)
		return nil, nil
	}
	if resp.Code != "0" {
		mylog.Logger.Error("QueryFile: backup sys return resp code !=0")
		return nil, err
	}

	if resp.Detail != nil {
		resp.Num = len(resp.Detail)
	}
	mylog.Logger.Debug("QueryFile:%v", resp)
	return &resp, nil

}

// Get backuppai get file
func (task *QueryReq) Get(params QueryReq) ([]byte, error) {

	client := &http.Client{}
	url := fmt.Sprintf(BackupURL + "/query")
	jsonData, err := json.Marshal(params)
	if err != nil {
		mylog.Logger.Error("param marshal fail:%v", err)
	}
	req, err := http.NewRequest("GET", url, bytes.NewBuffer(jsonData))
	if err != nil {
		mylog.Logger.Error("http request get fail:%v", err)
	}
	mylog.Logger.Info("http request get success")
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		mylog.Logger.Error("http do request fail:%v", err)
	}
	defer resp.Body.Close()
	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		mylog.Logger.Error("read resp body fail:%v", err)
	}

	if !(resp.StatusCode >= 200 && resp.StatusCode < 300) {
		mylog.Logger.Error("resp code %d", resp.StatusCode)
	}
	mylog.Logger.Info("GetFile from api success")
	return respBody, nil
}
