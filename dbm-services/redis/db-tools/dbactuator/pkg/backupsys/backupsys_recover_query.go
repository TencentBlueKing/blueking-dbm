package backupsys

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"net/http"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RecoverQueryReq 备份系统下载结果请求体
type RecoverQueryReq struct {
	RecoverQueryParams `json:"params"`
}

// RecoverQueryParams 备份系统下载结果请求参数格式
type RecoverQueryParams struct {
	Version                 string `json:"version"`
	RecoverQueryRequestInfo `json:"request_info"`
}

// RecoverQueryRequestInfo 备份系统查询请求信息
type RecoverQueryRequestInfo struct {
	BaseInfo               `json:"base_info"`
	RecoverQueryDetailInfo `json:"detail_info"`
}

// RecoverQueryDetailInfo 查询拉取进度的参数
type RecoverQueryDetailInfo struct {
	// 恢复任务ID 用于查询拉取进度
	RecoverID string `json:"recoverid"`
	//目标IP，文件恢复到哪一台机器上的，就是这台机器的IP
	DestIP string `json:"dest_ip"`
}

// RecoverQueryResp 恢复文件下载任务的响应参数
type RecoverQueryResp struct {
	Code    string               `json:"code"`
	Msg     string               `json:"msg"`
	Todo    int                  `json:"todo"`
	Doing   int                  `json:"doing"`
	Success int                  `json:"success"`
	Fail    int                  `json:"fail"`
	Detail  []RecoverQueryDetail `json:"detail"`
}

// RecoverQueryDetail 备份文件信息
type RecoverQueryDetail struct {
	TaskID   string `json:"task_id"`
	FileName string `json:"filename"`
	Status   string `json:"status"`
	DestPath string `json:"dest_path"`
	StatusEn string `json:"status_en"`
}

// RecoverQueryPost backup api post
func (task *RecoverReq) RecoverQueryPost(params RecoverQueryReq) ([]byte, error) {

	client := &http.Client{}
	url := fmt.Sprintf(BackupURL + "/get_recover_result")
	jsonData, err := json.Marshal(params)
	if err != nil {
		mylog.Logger.Error("param marshal fail:%v", err)
	}
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		mylog.Logger.Error("http request get fail:%v", err)
	}
	mylog.Logger.Info("http request get success")

	req.Header.Set("Content-Type", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		mylog.Logger.Error("http do request fail:%v", err)
	}
	mylog.Logger.Debug("RecoverQueryPost:resp:%v", resp)
	defer resp.Body.Close()
	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		mylog.Logger.Error("read resp body fail:%v", err)
	}

	if !(resp.StatusCode >= 200 && resp.StatusCode < 300) {
		mylog.Logger.Error("resp code %d", resp.StatusCode)
	}
	mylog.Logger.Debug("RecoverQueryPost:respBody:%s", respBody)
	mylog.Logger.Info("request api success")
	return respBody, nil
}

// CheckRecoverTasksStatus 查询备份拉取状态
func (task *RecoverReq) CheckRecoverTasksStatus(params RecoverQueryReq) (*RecoverQueryResp, error) {
	err := util.ValidateStruct(params)
	if err != nil {
		mylog.Logger.Error("CheckRecoverTasksStatus:validate struct failed:%v", err)
		return nil, err
	}
	result, err := task.RecoverQueryPost(params)
	if err != nil {
		mylog.Logger.Error("CheckRecoverTasksStatus:RecoverQueryPost failed:%v", err)
		return nil, err
	}
	mylog.Logger.Debug("CheckRecoverTasksStatus:result:%s", result)
	var resp RecoverQueryResp
	err = json.Unmarshal(result, &resp)
	if err != nil {
		mylog.Logger.Error("CheckRecoverTasksStatus:json Unmarshal failed:%v", err)
		return nil, err
	}
	if resp.Code != "0" {
		mylog.Logger.Warn("CheckRecoverTasksStatus: resp return code != 0")
		return nil, errors.New(resp.Msg)
	}
	mylog.Logger.Debug("CheckRecoverTasksStatus success resp:%v", resp)
	mylog.Logger.Info("CheckRecoverTasksStatus success ")
	return &resp, nil

}
