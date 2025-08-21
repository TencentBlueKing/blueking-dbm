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
	commtypes "k8s-dbs/common/types"
)

var requestTypeMapping = map[string]string{
	"CreateCluster":        "创建集群",
	"DeleteCluster":        "删除集群",
	"UpdateCluster":        "全量更新集群",
	"PartialUpdateCluster": "局部更新集群",
	"StartCluster":         "启动集群",
	"StopCluster":          "停止集群",
	"RestartCluster":       "重启集群",
	"StartComponent":       "启动组件",
	"StopComponent":        "停止组件",
	"RestartComponent":     "重启组件",
	"VerticalScaling":      "垂直扩容",
	"HorizontalScaling":    "水平扩容",
	"VolumeExpansion":      "磁盘扩容",
	"UpgradeComp":          "升级组件",
	"ExposeService":        "暴露服务",
	"Undefined":            "未知操作",
	"CreateK8sNs":          "创建命名空间",
	"DeleteK8sPod":         "删除 Pod 实例",
}

// ClusterOperationLogResponse response vo 定义
type ClusterOperationLogResponse struct {
	ID               uint64                 `json:"id"`
	RequestID        string                 `json:"requestId"`
	K8sClusterName   string                 `json:"k8sClusterName"`
	ClusterName      string                 `json:"clusterName"`
	NameSpace        string                 `json:"namespace"`
	RequestType      string                 `json:"requestType"`
	RequestTypeAlias string                 `json:"requestTypeAlias"`
	RequestParams    string                 `json:"requestParams"`
	Status           string                 `json:"status"`
	Description      string                 `json:"description"`
	CreatedBy        string                 `json:"createdBy"`
	CreatedAt        commtypes.JSONDatetime `json:"createdAt"`
	UpdatedBy        string                 `json:"updatedBy"`
	UpdatedAt        commtypes.JSONDatetime `json:"updatedAt"`
}

// MarshalJSON 自定义 ClusterOperationLogResponse JSON 序列化逻辑
func (k ClusterOperationLogResponse) MarshalJSON() ([]byte, error) {
	k.RequestTypeAlias = requestTypeMapping[k.RequestType]
	output := map[string]interface{}{
		"id":               k.ID,
		"requestId":        k.RequestID,
		"k8sClusterName":   k.NameSpace,
		"clusterName":      k.ClusterName,
		"nameSpace":        k.NameSpace,
		"requestType":      k.RequestType,
		"requestTypeAlias": k.RequestTypeAlias,
		"requestParams":    k.RequestParams,
		"status":           k.Status,
		"description":      k.Description,
		"createdBy":        k.CreatedBy,
		"createdAt":        k.CreatedAt,
		"updatedBy":        k.UpdatedBy,
		"updatedAt":        k.UpdatedAt,
	}
	return json.Marshal(output)
}
