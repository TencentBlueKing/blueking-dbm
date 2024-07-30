package doris

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/hdfs/util"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/pkg/errors"
)

// CheckDecommissionParams TODO
type CheckDecommissionParams struct {
	Host      string              `json:"host" validate:"required,ip" ` // 本机IP
	QueryPort int                 `json:"query_port" validate:"required"`
	HttpPort  int                 `json:"http_port" validate:"required"`
	UserName  string              `json:"username" validate:"required"`
	Password  string              `json:"password" validate:"required"`
	HostMap   map[string][]string `json:"host_map" validate:"required"`
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
	// 通过http判断节点是否退役
	urlFormat := "http://%s:%s@%s:%d/rest/v1/system?path=//backends"
	responseBody, err := util.HttpGet(fmt.Sprintf(urlFormat, c.Params.UserName, c.Params.Password,
		c.Params.Host, c.Params.HttpPort))
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

// CheckDecommissionResponse 检查节点退役响应 结构体
type CheckDecommissionResponse struct {
	Message string                `json:"msg"`
	Code    int                   `json:"code"`
	Count   int                   `json:"count"`
	Data    CheckDecommissionData `json:"data"`
}
