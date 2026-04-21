/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package response

// CreateClbAPIResponse CLB API 创建响应
type CreateClbAPIResponse struct {
	Result  bool        `json:"result"`
	Data    []string    `json:"data"` // 返回 clb_id列表
	Code    string      `json:"code"`
	Message string      `json:"message"`
	Errors  interface{} `json:"errors"`
}

// GetClbAPIResponse CLB API 获取响应
type GetClbAPIResponse struct {
	Result  bool        `json:"result"`
	Data    []ClbItem   `json:"data"`
	Code    string      `json:"code"`
	Message string      `json:"message"`
	Errors  interface{} `json:"errors"`
}

// ClbItem CLB 信息
type ClbItem struct {
	LoadBalancerID   string   `json:"LoadBalancerId"`
	LoadBalancerName string   `json:"LoadBalancerName"`
	LoadBalancerType string   `json:"LoadBalancerType"`
	LoadBalancerVips string   `json:"LoadBalancerVips"`
	VpcID            string   `json:"VpcId"`
	Zones            []string `json:"Zones"`
}
