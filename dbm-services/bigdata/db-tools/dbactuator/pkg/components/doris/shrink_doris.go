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

// CheckDecommission TODO
func (c *CheckDecommissionService) CheckDecommission() (err error) {
	decommissioningErr := errors.New("Backend Decommissioning")
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
		return err
	}
	var response CheckDecommissionResponse
	if err = json.Unmarshal(responseBody, &response); err != nil {
		logger.Error("transfer response to json failed", err.Error())
		return err
	}
	data := response.Data
	if &data != nil {
		for _, backendInfo := range data.Rows {
			// backend 属于要下架的IP
			decommissionState, err := strconv.ParseBool(backendInfo.SystemDecommissioned)
			if err != nil {
				logger.Error("transfer response backend info SystemDecommissioned to bool failed", err.Error())
				return err
			} else if !decommissionState {
				// 非 退役节点，跳过
				continue
			}
			tabletNum, err := strconv.Atoi(backendInfo.TabletNum)
			if err != nil {
				logger.Error("transfer response backend info tablet num to int failed", err.Error())
				return err
			} else if tabletNum > 0 {
				logger.Error("backend ip is %s, tablet num is %d, cannot drop", backendInfo.Host, tabletNum)
				return decommissioningErr
			}
		}
	} else {
		logger.Error("transfer response to CheckDecommissionData failed ", err.Error())
		return decommissioningErr
	}

	logger.Info("Backend Decommission completed")
	return nil
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
