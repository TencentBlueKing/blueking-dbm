package backupsys

import (
	"bytes"
	"encoding/json"
	"fmt"
	"github.com/pkg/errors"
	"io"
	"net/http"
)

type requestReq struct {
	Params struct {
		Version     string `json:"version"`
		RequestInfo struct {
			BaseInfo   BaseInfo   `json:"base_info"`
			DetailInfo DetailInfo `json:"detail_info"`
		} `json:"request_info"`
	} `json:"params"`
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

// RespCommon  查询备份文件的响应内容
type RespCommon struct {
	Code      string `json:"code"`
	Msg       string `json:"msg"`
	RecoverId string `json:"recoverid,omitempty"` // Recover接口有用到
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

// QueryApi 执行查询接口
func QueryApi(queryApiUrl, sysId, sysKey, sysTicket string, sourceIp, beginDate, endDate, fileName string) (*QueryResp, error) {
	url := queryApiUrl
	req := new(requestReq)
	req.Params.Version = "1.0"
	req.Params.RequestInfo.BaseInfo.SysID = sysId
	req.Params.RequestInfo.BaseInfo.Ticket = sysTicket
	req.Params.RequestInfo.BaseInfo.Key = sysKey
	req.Params.RequestInfo.DetailInfo.SourceIP = sourceIp
	req.Params.RequestInfo.DetailInfo.BeginDate = beginDate
	req.Params.RequestInfo.DetailInfo.EndDate = endDate
	req.Params.RequestInfo.DetailInfo.FileName = fileName

	body, err := doRequest(http.MethodGet, url, req)
	if err != nil {
		return nil, err
	}
	result := &RespCommon{}
	err = json.Unmarshal(body, result)
	if err != nil {
		return nil, err
	}

	// check response and data is nil
	if result.Code != "0" {
		return nil, errors.New(result.Msg)
	}

	resultOk := QueryResp{}
	err = json.Unmarshal(body, &resultOk)
	if err != nil {
		return nil, err
	}
	return &resultOk, nil
}

// doRequest 调用bkapi，返回CommonResponse
func doRequest(method, url string, body interface{}) ([]byte, error) {
	client := &http.Client{}
	var req *http.Request
	var err error
	if body != nil {
		in, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		req, err = http.NewRequest(method, url, bytes.NewBuffer(in))
		// log.Printf("request req %+v err %v", req, err)
	} else {
		req, err = http.NewRequest(method, url, nil)
	}

	if err != nil {
		return nil, errors.Wrap(err, "NewRequest")
	}

	req.Header.Set("Content-type", "application/json")

	var resp *http.Response
	if resp, err = client.Do(req); err != nil {
		return nil, errors.Wrap(err, "doReq")
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("http error: %v", resp.StatusCode)
	}
	return io.ReadAll(resp.Body)
}
