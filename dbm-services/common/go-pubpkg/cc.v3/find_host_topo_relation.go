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

// FindHostTopoRelation TODO
type FindHostTopoRelation struct {
	client *Client
	url    string
}

// FindHostTopoRelationParam TODO
type FindHostTopoRelationParam struct {
	BkBizID     int   `json:"bk_biz_id"`
	BkSetIds    []int `json:"bk_set_ids"`
	BkModuleIds []int `json:"bk_module_ids"`
	BkHostIds   []int `json:"bk_host_ids" url:"bk_host_ids"`
	// 分页信息
	Page BKPage `json:"page"`
}

// FindHostTopoRelationResponeData TODO
type FindHostTopoRelationResponeData struct {
	Count int             `json:"count"`
	Data  []HostBizModule `json:"data"`
	Page  BKPage          `json:"page"`
}

// NewFindHostTopoRelation returns a new FindHostTopoRelation server
func NewFindHostTopoRelation(client *Client) *FindHostTopoRelation {
	return &FindHostTopoRelation{
		client: client,
		url:    "/api/c/compapi/v2/cc/find_host_topo_relation/",
	}
}

// Query do query handler
func (h *FindHostTopoRelation) Query(param *FindHostTopoRelationParam) (FindHostTopoRelationResponeData, *Response,
	error) {
	resp, err := h.client.Do(http.MethodPost, h.url, param)
	if err != nil {
		return FindHostTopoRelationResponeData{}, resp, err
	}
	var result FindHostTopoRelationResponeData
	err = json.Unmarshal(resp.Data, &result)
	if err != nil {
		return FindHostTopoRelationResponeData{}, resp, err
	}
	return result, resp, nil
}
