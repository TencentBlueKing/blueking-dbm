/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dbmapi

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/url"

	"dbm-services/common/go-pubpkg/logger"
)

// UworkFaultResponse uwork fault response
type UworkFaultResponse struct {
	BkHostID       int      `json:"bk_host_id"`       // 主机ID
	HasOpenTickets bool     `json:"has_open_tickets"` // 是否有未关闭的工单
	OpenTicketIDs  []string `json:"open_ticket_ids"`  // 未关闭的工单ID列表
}

// XworkFaultResponse xwork fault response
type XworkFaultResponse struct {
	TaskId          int     `json:"TaskId"`
	VmUuid          string  `json:"VmUuid"`
	TaskStatus      int     `json:"TaskStatus"`
	StartTime       string  `json:"StartTime"`
	EndTime         string  `json:"EndTime"`
	TaskTypeId      int     `json:"TaskTypeId"`
	BsiIp           string  `json:"BsiIp"`
	DeptId          int     `json:"DeptId"`
	SvrOperator     string  `json:"SvrOperator"`
	SvrBakOperator  string  `json:"SvrBakOperator"`
	BsiPath         string  `json:"BsiPath"`
	AssetId         string  `json:"AssetId"`
	TaskStatusCN    string  `json:"TaskStatusCN"`
	TaskTypeCN      string  `json:"TaskTypeCN"`
	TaskDetail      string  `json:"TaskDetail"`
	SvrInstanceType string  `json:"SvrInstanceType"`
	InstanceId      string  `json:"InstanceId"`
	VmAlias         string  `json:"VmAlias"`
	DeptName        string  `json:"DeptName"`
	AuthTime        *string `json:"AuthTime"` // 使用指针类型处理可能的 null 值
	HostFaultType   string  `json:"HostFaultType"`
	MainTaskId      string  `json:"MainTaskId"`
	AuthType        string  `json:"AuthType"`
}

// DbmFaultResponseItem dbm fault response item
type DbmFaultResponseItem struct {
	Uwork UworkFaultResponse `json:"uwork"`
	Xwork XworkFaultResponse `json:"xwork"`
}

func (u UworkFaultResponse) isOk() bool {
	return !u.HasOpenTickets && len(u.OpenTicketIDs) == 0
}

func (x XworkFaultResponse) isOk() bool {
	return x.TaskId <= 0
}

// CheckIsOK check if the fault response item is OK
func (x DbmFaultResponseItem) CheckIsOK() bool {
	return x.Uwork.isOk() && x.Xwork.isOk()
}

// CheckFaultHostsParamItem check fault hosts param item
type CheckFaultHostsParamItem struct {
	IP       string `json:"ip"`
	BkHostID int    `json:"bk_host_id"` // 主机ID
}

// CheckFaultHosts request dbm api to check fault hosts
func CheckFaultHosts(hosts []CheckFaultHostsParamItem) (d map[string]DbmFaultResponseItem, err error) {
	var content []byte
	cli := NewDbmClient()
	u, err := url.JoinPath(cli.EndPoint, DBMFaultHostsCheckApi)
	if err != nil {
		return nil, err
	}
	p := map[string]interface{}{
		"hosts": hosts,
	}
	body, err := json.Marshal(p)
	if err != nil {
		logger.Error("marshal CheckFaultHosts body failed %s ", err.Error())
		return nil, err
	}
	request, err := http.NewRequest(http.MethodPost, u, bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	resp, err := cli.Client.Do(request)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	content, err = io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("read response body failed %s", err.Error())
		return nil, err
	}
	logger.Info("response %v", string(content))
	if err = json.Unmarshal(content, &d); err != nil {
		return nil, err
	}
	return d, nil
}
