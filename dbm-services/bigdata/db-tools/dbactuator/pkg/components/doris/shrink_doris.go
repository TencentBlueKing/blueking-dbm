package doris

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/dorisutil"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"
	"net/url"
	"strconv"
	"time"

	"github.com/pkg/errors"
)

const (
	// CheckDecommissionRetryTimes 检查 BE 退役进度的最大重试次数。
	// 单次执行最多轮询 10 次，最多发生 9 次等待，配合 CheckDecommissionWaitTime=5min，
	// 总等待时长上限约 45 分钟（外加每次 HTTP 请求耗时），控制在作业平台单次脚本执行超时（3600s）以内，
	// 避免被作业平台强杀导致真实失败原因丢失。
	// 超过上限后本 actor 返回失败，由人工在 dbm 流程上重试；本检查为只读操作，可安全重复执行。
	CheckDecommissionRetryTimes = 10
	// CheckDecommissionWaitTime 每次重试之间的等待时间
	CheckDecommissionWaitTime = 5 * time.Minute
)

// CheckDecommissionParams TODO
type CheckDecommissionParams struct {
	Host         string              `json:"host" validate:"required,ip" ` // 本机IP
	QueryPort    int                 `json:"query_port" validate:"required"`
	HttpPort     int                 `json:"http_port" validate:"required"`
	UserName     string              `json:"username" validate:"required"`
	Password     string              `json:"password" validate:"required"`
	HostMap      map[string][]string `json:"host_map" validate:"required"`
	RootPassword string              `json:"root_password" validate:"omitempty"`
}

// CheckDecommissionService TODO
type CheckDecommissionService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *CheckDecommissionParams
	RollBackContext rollback.RollBackObjects
}

// CheckDecommission 循环检查 BE 节点退役进度，直到退役完成或超过最大重试次数。
// 增加重试：每次调用 checkDecommissionOnce 判断是否完成；
// 未完成且后面仍有重试机会时，等待 CheckDecommissionWaitTime 后继续重试，最多检查 CheckDecommissionRetryTimes 次。
func (c *CheckDecommissionService) CheckDecommission() (err error) {
	logger.Info("start checking BE decommission progress, max retry %d times, interval %s",
		CheckDecommissionRetryTimes, CheckDecommissionWaitTime)

	for i := 0; i < CheckDecommissionRetryTimes; i++ {
		done, checkErr := c.checkDecommissionOnce()
		if checkErr != nil {
			// request or parse error, return immediately without retry
			logger.Error("check BE decommission progress failed: %s", checkErr.Error())
			return checkErr
		}
		if done {
			logger.Info("Backend Decommission completed")
			return nil
		}

		if i < CheckDecommissionRetryTimes-1 {
			logger.Info("BE is still decommissioning, check %d/%d not finished, wait %s and retry",
				i+1, CheckDecommissionRetryTimes, CheckDecommissionWaitTime)
			time.Sleep(CheckDecommissionWaitTime)
		}
	}

	return fmt.Errorf("BE decommission still not finished after %d attempts", CheckDecommissionRetryTimes)
}

// checkDecommissionOnce 单次检查 BE 节点退役进度。
// 返回值：
//   - done == true 表示所有处于退役状态的 BE 节点 tablet 数都已为 0，退役完成；
//   - done == false && err == nil 表示仍有 BE 节点 tablet 数 > 0，尚在退役中，调用方应继续重试；
//   - err != nil 表示请求/解析等异常，调用方应中止重试并返回错误。
func (c *CheckDecommissionService) checkDecommissionOnce() (done bool, err error) {
	rootPwd := dorisutil.DefaultString(c.Params.RootPassword, c.Params.Password)

	// 通过http判断节点是否退役
	// 使用 url.UserPassword 构造 userinfo，避免密码包含 @ : / # ? 等特殊字符时被 URL 解析截断
	u := &url.URL{
		Scheme:   "http",
		User:     url.UserPassword(RootUser, rootPwd),
		Host:     fmt.Sprintf("%s:%d", c.Params.Host, c.Params.HttpPort),
		Path:     "/rest/v1/system",
		RawQuery: "path=//backends",
	}
	responseBody, err := util.HttpGet(u.String())
	if err != nil {
		return false, err
	}
	var response CheckDecommissionResponse
	if err = json.Unmarshal(responseBody, &response); err != nil {
		logger.Error("transfer response to json failed: %s", err.Error())
		return false, err
	}

	data := response.Data
	// 同时覆盖两种异常：JSON 里没有 rows 字段（nil slice） 与 "rows": [] （len 0 的非 nil slice）。
	// 前一种可能是接口结构变更；后一种可能是接口异常/参数错——两者都不应被判定为"退役完成"。
	if len(data.Rows) == 0 {
		logger.Error("backends rows is empty in FE response")
		return false, errors.New("empty backends rows returned by FE")
	}

	for _, backendInfo := range data.Rows {
		decommissionState, parseErr := strconv.ParseBool(backendInfo.SystemDecommissioned)
		if parseErr != nil {
			logger.Error("transfer response backend info SystemDecommissioned to bool failed: %s", parseErr.Error())
			return false, parseErr
		}
		if !decommissionState {
			// 非退役节点，跳过
			continue
		}
		tabletNum, parseErr := strconv.Atoi(backendInfo.TabletNum)
		if parseErr != nil {
			logger.Error("transfer response backend info tablet num to int failed: %s", parseErr.Error())
			return false, parseErr
		}
		if tabletNum > 0 {
			logger.Info("backend ip is %s, tablet num is %d, still decommissioning",
				backendInfo.Host, tabletNum)
			return false, nil
		}
	}

	return true, nil
}

// BackendInfo BE信息 结构体
type BackendInfo struct {
	Host                 string `json:"Host"`
	SystemDecommissioned string `json:"SystemDecommissioned"`
	TabletNum            string `json:"TabletNum"`
	Alive                string `json:"Alive"`
}

// CheckDecommissionData 检查退役信息 结构体
type CheckDecommissionData struct {
	ColumnNames []string      `json:"column_names"`
	Rows        []BackendInfo `json:"rows"`
}

// BeHealthPort BE 节点健康检查 HTTP 端口
const BeHealthPort = 8040

// BeHealthResponse BE /api/health 接口返回
type BeHealthResponse struct {
	Status  string `json:"status"`
	Message string `json:"msg"`
}

// CheckBackendsAliveParams 检查BE节点是否已加入集群 参数
type CheckBackendsAliveParams struct {
	HostMap map[string][]string `json:"host_map" validate:"required"`
}

// CheckBackendsAliveService 检查BE节点是否已加入集群
type CheckBackendsAliveService struct {
	GeneralParam *components.GeneralParam
	InstallParams
	Params          *CheckBackendsAliveParams
	RollBackContext rollback.RollBackObjects
}

// CheckBackendsAlive 对 host_map 中每个 BE 直接调用 /api/health，确认全部返回 OK
func (c *CheckBackendsAliveService) CheckBackendsAlive() (err error) {
	RetryCount := 12
	SleepDuration := 10 * time.Second

	// 收集所有待检查的 BE IP
	expectedBackends := make(map[string]bool)
	for _, hosts := range c.Params.HostMap {
		for _, host := range hosts {
			expectedBackends[host] = true
		}
	}
	logger.Info("CheckBackendsAlive: checking %d BEs on port %d", len(expectedBackends), BeHealthPort)

	for retryTimes := 0; retryTimes <= RetryCount; retryTimes++ {
		allAlive := true
		for host := range expectedBackends {
			url := fmt.Sprintf("http://%s:%d/api/health", host, BeHealthPort)
			responseBody, httpErr := util.HttpGet(url)
			if httpErr != nil {
				logger.Info("CheckBackendsAlive attempt %d/%d: BE %s not ready, err=%v",
					retryTimes+1, RetryCount+1, host, httpErr)
				allAlive = false
				break
			}

			var resp BeHealthResponse
			if jsonErr := json.Unmarshal(responseBody, &resp); jsonErr != nil {
				logger.Info("CheckBackendsAlive attempt %d/%d: BE %s response parse failed, err=%v",
					retryTimes+1, RetryCount+1, host, jsonErr)
				allAlive = false
				break
			}

			if resp.Status != "OK" {
				logger.Info("CheckBackendsAlive attempt %d/%d: BE %s status=%s, msg=%s",
					retryTimes+1, RetryCount+1, host, resp.Status, resp.Message)
				allAlive = false
				break
			}
		}

		if allAlive {
			logger.Info("CheckBackendsAlive success on attempt %d, all %d BEs are alive",
				retryTimes+1, len(expectedBackends))
			return nil
		}

		time.Sleep(SleepDuration)
	}

	return errors.New("CheckBackendsAlive: retry all failed, not all BEs are alive")
}

// CheckDecommissionResponse 检查节点退役响应 结构体
type CheckDecommissionResponse struct {
	Message string                `json:"msg"`
	Code    int                   `json:"code"`
	Count   int                   `json:"count"`
	Data    CheckDecommissionData `json:"data"`
}
