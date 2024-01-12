package backupsys

import (
	"encoding/json"
	log "github.com/sirupsen/logrus"
	"net/http"
)

// RecoverReq Recover Req struct
type RecoverReq struct {
	Params struct {
		Version     string `json:"version"`
		RequestInfo struct {
			BaseInfo   BaseInfo `json:"base_info"`
			DetailInfo struct {
				TaskIdList  string `json:"taskid_list"`
				DestIP      string `json:"dest_ip"`
				LoginUser   string `json:"login_user"`
				LoginPasswd string `json:"login_passwd"`
				Diretory    string `json:"diretory"` // json拼写错误.. sb
				Reason      string `json:"reason"`
			} `json:"detail_info"`
		} `json:"request_info"`
	} `json:"params"`
}

// RecoverApi 发起回档需求.
func RecoverApi(bsRecoverApi, sysId, sysKey, sysTicket string, taskIdList string, destIP, destLoginUser, destLoginPass, destDir, reason string) (string, error) {
	req := new(RecoverReq)
	req.Params.Version = "1.0"
	req.Params.RequestInfo.BaseInfo.SysID = sysId
	req.Params.RequestInfo.BaseInfo.Ticket = sysTicket
	req.Params.RequestInfo.BaseInfo.Key = sysKey
	req.Params.RequestInfo.DetailInfo.TaskIdList = taskIdList
	req.Params.RequestInfo.DetailInfo.DestIP = destIP
	req.Params.RequestInfo.DetailInfo.LoginUser = destLoginUser
	req.Params.RequestInfo.DetailInfo.LoginPasswd = destLoginPass
	req.Params.RequestInfo.DetailInfo.Diretory = destDir
	req.Params.RequestInfo.DetailInfo.Reason = reason

	body, err := doRequest(http.MethodGet, bsRecoverApi, req)

	if err != nil {
		return "", err
	}
	result := &RespCommon{}
	err = json.Unmarshal(body, result)
	log.Printf("RecoverApi result: %+v", result)
	if err != nil {
		return "", err
	}
	return result.RecoverId, nil
}
