/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cc

import (
	"encoding/json"
	"net/http"
)

// ListAgentState TODO
type ListAgentState struct {
	client *Client
	Url    string
}

// NewListAgentState TODO
// NewListBizHosts returns a new ListBizHosts server
func NewListAgentState(client *Client) *ListAgentState {
	return &ListAgentState{
		client: client,
		Url:    "/core/api/ipchooser_host/details/",
	}
}

// ListAgentInfoParam TODO
type ListAgentInfoParam struct {
	// 最大支持1000个ID的查询
	HostList  []IpchooserHost `json:"host_list"`
	AllScope  bool            `json:"all_scope"`
	ScopeList []Scope         `json:"scope_list"`
}

// IpchooserHost ipchooser host
type IpchooserHost struct {
	HostId int               `json:"host_id"`
	Meta   IpchooserHostMeta `json:"meta"`
}

// IpchooserHostMeta ipchooser host meta
type IpchooserHostMeta struct {
	ScopeType string `json:"scope_type"`
	ScopeId   string `json:"scope_id"`
	BkBizId   int    `json:"bk_biz_id"`
}

// Scope scope
type Scope struct {
	ScopeType string `json:"scope_type"`
	ScopeId   string `json:"scope_id"`
}

// ListAgentInfoRespone list agent info
// nolint
type ListAgentInfoRespone struct {
	BkAgentId string `json:"bk_agent_id"`
	BkCloudID int    `json:"bk_cloud_id"`
	HostId    int    `json:"host_id"`
	Ip        string `json:"ip"`
	// NOT_ALIVE = 0
	// ALIVE = 1
	// TERMINATED = 2
	// NOT_INSTALLED = 3
	BkAgentAlive int `json:"bk_agent_alive"`
}

// QueryListAgentInfo 查询主机gseAgent转态
func (h *ListAgentState) QueryListAgentInfo(param *ListAgentInfoParam) ([]ListAgentInfoRespone, *Response, error) {
	resp, err := h.client.Do(http.MethodPost, h.Url, param)
	if err != nil {
		return nil, resp, err
	}
	var result []ListAgentInfoRespone
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, resp, err
	}
	return result, resp, nil
}
