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
	"fmt"
	"net/http"
)

// 功能描述
// 根据业务ID查询业务下的主机，可附带其他的过滤信息，如集群id,模块id等

// ListBizHosts TODO
type ListBizHosts struct {
	client *Client
	url    string
}

// NewListBizHosts returns a new ListBizHosts server
func NewListBizHosts(client *Client) *ListBizHosts {
	return &ListBizHosts{
		client: client,
		url:    "/api/c/compapi/v2/cc/list_biz_hosts/",
	}
}

// NewListBizHostsGw by pass api gw
func NewListBizHostsGw(client *Client, bkBizId string) *ListBizHosts {
	return &ListBizHosts{
		client: client,
		url:    fmt.Sprintf("/api/v3/hosts/app/%s/list_hosts", bkBizId),
	}
}

// QueryListBizHosts 查询业务下的主机
func (h *ListBizHosts) QueryListBizHosts(param *ListBizHostsParam) (*ListBizHostsResponse, *Response, error) {
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return nil, resp, err
	}
	var result ListBizHostsResponse
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return nil, resp, err
	}
	return &result, resp, nil
}
