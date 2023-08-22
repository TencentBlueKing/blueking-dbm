package backupsys

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RecoverReq 备份系统下载请求体
type RecoverReq struct {
	RecoverParams `json:"params"`
}

// RecoverParams 备份系统下载请求参数格式
type RecoverParams struct {
	Version            string `json:"version"`
	RecoverRequestInfo `json:"request_info"`
}

// RecoverRequestInfo 备份系统查询请求信息
type RecoverRequestInfo struct {
	BaseInfo          `json:"base_info"`
	RecoverDetailInfo `json:"detail_info"`
}

// RecoverDetailInfo 请求下载文件的参数
type RecoverDetailInfo struct {
	// taskid列表，该列表由根据备份查询接口返回的数据自由组合
	TaskidList string `json:"taskid_list,omitempty" example:"10000,100001"`
	// 目标IP，文件恢复到哪一台机器上的，就是这台机器的IP
	DestIP string `json:"dest_ip" validate:"required,ip" example:"x.x.x.x"`
	// 登录 dest_ip 的用户名，下载后的文件属组是该用户
	LoginUser string `json:"login_user" validate:"required"`
	// 登录 dest_ip 的用户名的密码, ieg 传统scp 方式下载才需要。如果是 cos 下载则不需要
	LoginPasswd string `json:"login_passwd,omitempty"`
	// 文件恢复到哪个目录
	Directory string `json:"diretory" validate:"required" example:"/data/dbbak"` // diretory 是备份系统参数错误拼写
	// 恢复原因（备注用途）
	Reason string `json:"reason"`
}

// RecoverResp 拉取备份响应内容
type RecoverResp struct {
	Code string `json:"code"`
	Msg  string `json:"msg"`
	// 恢复任务ID 用于查询拉取进度
	RecoverID string `json:"recoverid"`
}

// WaitForRecoverFinish 根据 backup task_id 异步下载文件并等待完成
func (task *RecoverReq) WaitForRecoverFinish(params RecoverReq, destIP string) (err error) {
	// 异步下载备份文件
	recoverID, err := task.RecoverFile(params)
	if err != nil {
		mylog.Logger.Error("WaitForRecoverFinish:RecoverFile failed")
		return err
	}
	mylog.Logger.Info("recoverID:%s", recoverID)
	recoverQueryParams := RecoverQueryReq{
		RecoverQueryParams: RecoverQueryParams{
			Version: consts.BackupVersion,
			RecoverQueryRequestInfo: RecoverQueryRequestInfo{
				BaseInfo: BaseInfo{
					SysID:  BackupSysID,
					Key:    BackupKey,
					Ticket: "",
				},
				RecoverQueryDetailInfo: RecoverQueryDetailInfo{
					RecoverID: recoverID,
					DestIP:    destIP,
				},
			},
		},
	}
	retryTimeLimit := 180
	// 获取下载状态
	for {
		if retryTimeLimit == 0 {
			break
		}
		result, err := task.CheckRecoverTasksStatus(recoverQueryParams)
		if err != nil {
			if retryTimeLimit > 0 {
				mylog.Logger.Warn("WaitForRecoverFinish:CheckRecoverTasksStatus info:%v", err)
				retryTimeLimit--
				time.Sleep(10 * time.Second)
				continue
			}
			mylog.Logger.Error("CheckRecoverTasksStatus fail recoverId:%s,retry times:%d,queryParams:%v,err:%v",
				recoverID, retryTimeLimit, recoverQueryParams, err)
			return err
		}
		mylog.Logger.Info("CheckRecoverTasksStatus finish")
		if result.Fail > 0 {
			err = fmt.Errorf("WaitForRecoverFinish:download result %s", result.Detail)
			mylog.Logger.Error(err.Error())
			return err
		}
		mylog.Logger.Debug("WaitForRecoverFinish result:%v", result)
		mylog.Logger.Info("WaitForRecoverFinish result")
		break
	}
	return nil

}

// RecoverFile 拉取备份文件 根据 backup task_id 异步下载文件
func (task *RecoverReq) RecoverFile(params RecoverReq) (string, error) {
	err := util.ValidateStruct(params)
	if err != nil {
		mylog.Logger.Error("RecoverFile:validate struct failed:%v", err)
		return "", err
	}
	var recoverID string = "0"
	respBody, err := task.Post(params)
	if err != nil {
		mylog.Logger.Error("RecoverFile:recover backup sys :%v", err)
		return recoverID, err
	}

	var resp RecoverResp
	err = json.Unmarshal(respBody, &resp)
	if err != nil {
		mylog.Logger.Error("RecoverFile:Unmarshal failed:%v", err)
		return recoverID, err
	}
	if resp.Code != "0" {
		mylog.Logger.Error("RecoverFile: backup sys return resp code !=0")
		return recoverID, err
	}
	mylog.Logger.Info("RecoverFile return result:%v", resp)
	recoverID = resp.RecoverID
	return recoverID, nil

}

// Post backup api post
func (task *RecoverReq) Post(params RecoverReq) ([]byte, error) {

	client := &http.Client{}
	url := fmt.Sprintf(BackupURL + "/recover")
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
	defer resp.Body.Close()
	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		mylog.Logger.Error("read resp body fail:%v", err)
	}

	if !(resp.StatusCode >= 200 && resp.StatusCode < 300) {
		mylog.Logger.Error("resp code %d", resp.StatusCode)
	}
	mylog.Logger.Info("request api success")
	return respBody, nil
}
