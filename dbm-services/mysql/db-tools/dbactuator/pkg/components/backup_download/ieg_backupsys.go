package backup_download

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/common/go-pubpkg/validate"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/pkg/errors"
)

// IBS = IegBackupSystem

const (
	// BACKUP_TASK_SUCC TODO
	BACKUP_TASK_SUCC string = "4"
	// FILE_EXPIRED TODO
	FILE_EXPIRED string = "1"
	// FILE_NOT_EXPIRED TODO
	FILE_NOT_EXPIRED string = "0"
	// MYSQL_FULL_BACKUP TODO
	MYSQL_FULL_BACKUP string = "MYSQL_FULL_BACKUP"
	// INCREMENT_BACKUP TODO
	INCREMENT_BACKUP string = "INCREMENT_BACKUP"
	// MYSQL_PRIV_FILE TODO
	MYSQL_PRIV_FILE string = "MYSQL_PRIV_FILE"
	// MYSQL_INFO_FILE TODO
	MYSQL_INFO_FILE string = "MYSQL_INFO_FILE"
)

// IBSParams 备份系统请求参数的格式
type IBSParams struct {
	Params struct {
		Version     string `json:"version"`
		RequestInfo struct {
			BaseInfo   *IBSBaseInfo `json:"base_info"`
			DetailInfo interface{}  `json:"detail_info"`
		} `json:"request_info"`
	} `json:"params"`
}

// NewIBSParams TODO
func NewIBSParams(info *IBSBaseInfo) *IBSParams {
	params := &IBSParams{}
	params.Params.Version = "1.0"
	params.Params.RequestInfo.BaseInfo = info
	return params
}

// IBSBaseInfo godoc
type IBSBaseInfo struct {
	// ieg 备份系统 api url 地址，会在后面拼接 /query /recover 后缀进行请求
	// 可从环境变量获取 IBS_INFO_url
	Url string `json:"url" validate:"required" example:"http://127.0.0.1/backupApi" env:"IBS_INFO_url" envDefault:"http://127.0.0.1/backupApi"`
	// application标识，亦即哪个系统需要访问本接口，可从环境变量获取 IBS_INFO_sys_id
	SysID string `json:"sys_id" validate:"required" env:"IBS_INFO_sys_id"`
	// 16位字串，由备份系统分配，可从环境变量获取 IBS_INFO__key
	Key string `json:"key" validate:"required" env:"IBS_INFO_key,unset"`
	// OA验证的ticket，一个长串，通常附加在访问内网应用的URL上，主要用来验证用户身份，可以留空
	Ticket string `json:"ticket"`
}

// IBSQueryResult 查询备份文件的结果记录详情
type IBSQueryResult struct {
	// 任务ID，用于下载
	TaskId string `json:"task_id"`
	// 备份任务上报时间
	Uptime string `json:"uptime"`
	// 文件最后修改时间
	FileLastMtime string `json:"file_last_mtime"`
	// 上报该备份任务的IP
	SourceIp   string `json:"source_ip"`
	CreateTime string `json:"createTime"`  // 非备份系统字段，全备（截取文件名中的字段），binlog 打开文件读取
	SourcePort string `json:"source_port"` // 非备份系统字段
	Path       string `json:"path"`        // 非备份系统字段
	Md5        string `json:"md5"`

	FileName string `json:"file_name"`
	// 文件大小
	Size    string `json:"size"`
	FileTag string `json:"file_tag"`
	// 文件状态
	Status string `json:"status"`
	// 备份状态信息, 'done, success', 'Fail: bad md5' 等
	Bkstif     string `json:"bkstif"`
	ExpireTime string `json:"expire_time"`
	Expired    string `json:"expired"`
}

// BackupFileIsOk TODO
func (c IBSQueryResult) BackupFileIsOk() bool {
	return c.Status == BACKUP_TASK_SUCC && c.Expired == FILE_NOT_EXPIRED
}

// IBSQueryReq 查询备份文件的请求参数
type IBSQueryReq struct {
	// 来源IP，即提交备份任务的机器IP
	SourceIp string `json:"source_ip" validate:"required"`
	// 哪一天提交，起始时间
	BeginDate string `json:"begin_date" validate:"required"`
	// 哪一天提交，结束时间，与begin_date形成一个时间范围，建议begin_date与end_date形成的时间范围不要超过3天
	EndDate string `json:"end_date" validate:"required"`
	// 文件名
	FileName string `json:"filename" validate:"required"`
}

// IBSQueryResp 查询备份文件的响应内容
type IBSQueryResp struct {
	Code   string           `json:"code"`
	Msg    string           `json:"msg"`
	Detail []IBSQueryResult `json:"detail"`
	Num    int              `json:"num"`
}

// IBSQueryRespAbnormal 备份系统 api: 有结果时 detail 是一个 struct，无结果时 detail=""
// IBSQueryResp 的补充
type IBSQueryRespAbnormal struct {
	Code string `json:"code"`
	Msg  string `json:"msg"`

	Detail string `json:"detail"`
}

// IBSRecoverReq 请求下载文件的参数
type IBSRecoverReq struct {
	// taskid 列表，,逗号分隔。会根据 task_files 里的信息，追加到这里。这里一般不传值，在 task_files 里提供 task_id 或者 file_name
	TaskidList string `json:"taskid_list,omitempty" example:"10000,100001"`
	// 目标IP，文件恢复到哪一台机器上的
	DestIp string `json:"dest_ip" validate:"required,ip" example:"1.1.1.1"`
	// 登录 dest_ip 的用户名，下载后的文件属组是该用户
	LoginUser string `json:"login_user" validate:"required"`
	// 登录 dest_ip 的用户名的密码, ieg 传统scp 方式下载才需要。如果是 cos 下载则不需要
	LoginPasswd string `json:"login_passwd,omitempty"`
	Directory   string `json:"diretory" validate:"required" example:"/data/dbbak"` // diretory 是备份系统参数错误拼写
	// 恢复原因（备注用途）
	Reason string `json:"reason"`
}

// IBSRecoverResp TODO
type IBSRecoverResp struct {
	Code      string `json:"code"`
	Msg       string `json:"msg"`
	RecoverId string `json:"recoverid"`
}

// IBSRecoverQueryReq 查询恢复下载任务状态的请求参数
type IBSRecoverQueryReq struct {
	RecoverId string `json:"recoverid"`
	DestIp    string `json:"dest_ip"`
}

// IBSRecoverQueryResp 恢复下载任务的响应参数
type IBSRecoverQueryResp struct {
	Code string `json:"code"`
	Msg  string `json:"msg"`

	Todo    int `json:"todo"`
	Doing   int `json:"doing"`
	Success int `json:"success"`
	Fail    int `json:"fail"`
	Detail  []struct {
		TaskId   string `json:"task_id"`
		FileName string `json:"filename"`
		Status   string `json:"status"`
		DestPath string `json:"dest_path"`
		StatusEn string `json:"status_en"`
	} `json:"detail"`
}

// BsQuery 搜索备份系统中的文件
func (r *IBSQueryParam) BsQuery(param IBSQueryReq) (*IBSQueryResp, error) {
	if err := validate.GoValidateStruct(param, false, false); err != nil {
		return nil, err
	}
	url := fmt.Sprintf("%s%s", r.client.Url, "/query")
	params := NewIBSParams(&r.IBSInfo)
	params.Params.RequestInfo.DetailInfo = param
	logger.Info("request BsQuery %+v", r.IBSQueryReq)
	result, err := r.client.PostJson(url, params, nil)
	if err != nil {
		return nil, errors.WithMessage(err, "查询备份系统")
	}
	resp := IBSQueryResp{}
	if err := json.Unmarshal(result, &resp); err != nil {
		respAbn := IBSQueryRespAbnormal{}
		if err := json.Unmarshal(result, &respAbn); err != nil {
			return nil, err
		} else {
			resp.Code = respAbn.Code
			resp.Msg = respAbn.Msg
		}
	}
	if resp.Code != "0" {
		return nil, errors.WithMessage(errors.New(resp.Msg), "查询备份系统返回code!=0")
	}
	if resp.Detail != nil {
		resp.Num = len(resp.Detail)
	}
	logger.Info("response BsQuery %+v", resp)
	return &resp, nil
}

// ErrorMessage TODO
func (r IBSRecoverQueryResp) ErrorMessage() string {
	if r.Fail == 0 {
		return ""
	}
	var messages []string
	for _, item := range r.Detail {
		messages = append(messages, fmt.Sprintf("file:%s, error:%s", item.FileName, item.StatusEn))
	}
	return strings.Join(messages, "\n")
}

// NewRecoverTask 根据 backup task_id 异步下载文件
func (r *IBSRecoverParam) NewRecoverTask(param IBSRecoverReq) (string, error) {
	url := fmt.Sprintf("%s%s", r.client.Url, "/recover")
	params := NewIBSParams(&r.IBSInfo)
	params.Params.RequestInfo.DetailInfo = param
	logger.Info("request NewRecoverTask %+v", r.IBSRecoverReq)
	var recoverId string = "0"
	result, err := r.client.PostJson(url, params, nil)
	if err != nil {
		return recoverId, errors.WithMessage(err, "请求备份系统下载")
	}
	resp := IBSRecoverResp{}
	if err := json.Unmarshal(result, &resp); err != nil {
		return recoverId, err
	}
	logger.Info("response NewRecoverTask %+v", resp)
	if resp.Code != "0" {
		return recoverId, errors.New(resp.Msg)
	}
	recoverId = resp.RecoverId
	return recoverId, nil
}

// GetRecoverTaskStatus 查询下载任务的状态
func (r *IBSRecoverParam) GetRecoverTaskStatus(param IBSRecoverQueryReq) (*IBSRecoverQueryResp, error) {
	url := fmt.Sprintf("%s%s", r.client.Url, "/get_recover_result")
	params := NewIBSParams(&r.IBSInfo)
	params.Params.RequestInfo.DetailInfo = param
	result, err := r.client.PostJson(url, params, nil)
	if err != nil {
		return nil, err
	}
	resp := IBSRecoverQueryResp{}
	if err := json.Unmarshal(result, &resp); err != nil {
		return nil, err
	}
	if resp.Code != "0" {
		return nil, errors.New(resp.Msg)
	}
	return &resp, nil
}

// RecoverAndWaitDone 根据 backup task_id 异步下载文件
func (r *IBSRecoverParam) RecoverAndWaitDone(param IBSRecoverReq) error {
	total := len(r.taskIdSlice)
	if total == 0 {
		return nil
	}
	// 请求下载，异步
	recoverId, err := r.NewRecoverTask(param)
	if err != nil {
		return err
	}
	logger.Info("recoverId:%s", recoverId)

	queryParam := IBSRecoverQueryReq{
		RecoverId: recoverId,
		DestIp:    param.DestIp,
	}
	var times = r.maxQueryRetryTimes
	var failTimes = r.maxFailCheckNum
	process := []int{30, 60, 120, 180, 300}
	lastFeedBackTime := time.Now()
	var lastIndex = 0
	indexLen := len(process)
	// 循环请求下载结果
	for {
		res, err := r.GetRecoverTaskStatus(queryParam)
		if err != nil {
			if times > 0 {
				times--
				time.Sleep(10 * time.Second)
				continue
			}
			logger.Error(
				"GetRecoverTaskStatus fail (recoverId:%s,retryTimes:%d,error:%w,param:%v)",
				recoverId, times, err, queryParam,
			)
			return err
		}

		if res.Success == total {
			logger.Info("[%d/%d]success,recoverId:%s", res.Success, total, recoverId)
			break
		}
		if res.Fail > 0 {
			if failTimes > 0 {
				failTimes--
				time.Sleep(60 * time.Second)
				continue
			}
			err := errors.Errorf(
				"[%d/%d]failed pull %d files, recoverId:%s, detail:%s",
				res.Success, total, res.Fail, recoverId, res.ErrorMessage(),
			)
			logger.Error(err.Error())
			return err
		}

		if int(time.Now().Sub(lastFeedBackTime).Seconds()) > process[lastIndex] {
			logger.Info(
				"[%d/%d]todo:%d,doing:%d,success:%d,fail:%d,recoverId:%s",
				res.Success, total, res.Todo, res.Doing, res.Success, res.Fail, recoverId,
			)
			lastIndex++
			lastFeedBackTime = time.Now()
			if lastIndex > indexLen-1 {
				lastIndex = 0
			}
		}
		time.Sleep(10 * time.Second)
	}
	return nil
}
