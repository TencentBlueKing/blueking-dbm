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

import (
	"encoding/json"
	"k8s-dbs/metadata/vo/response"
)

// ClusterResponse response vo 定义
type ClusterResponse struct {
	*response.K8sCrdClusterResponse
	ClusterOpsStatus string `json:"clusterOpsStatus"`
}

// MarshalJSON 自定义 ClusterAddonResponse JSON 序列化逻辑
func (k ClusterResponse) MarshalJSON() ([]byte, error) {
	marshalJSON, err := k.K8sCrdClusterResponse.MarshalJSON()
	if err != nil {
		return nil, err
	}
	var baseMap map[string]interface{}
	if err := json.Unmarshal(marshalJSON, &baseMap); err != nil {
		return nil, err
	}
	baseMap["clusterOpsStatus"] = k.ClusterOpsStatus
	return json.Marshal(baseMap)
}
