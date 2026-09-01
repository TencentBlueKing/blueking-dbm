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

package request

import (
	commentity "k8s-dbs/common/entity"
)

// ClusterOperationLogsRequest represents the request data structure of record.
type ClusterOperationLogsRequest struct {
	RequestID               string  `json:"requestId" required:"true"`
	K8sClusterName          string  `json:"k8sClusterName" required:"true"`
	ClusterName             string  `json:"clusterName" required:"true"`
	NameSpace               string  `json:"namespace" required:"true"`
	RequestType             string  `json:"requestType" required:"true"`
	RequestParams           string  `json:"requestParams" required:"true"`
	TicketID                *uint64 `json:"ticketId"`
	Description             string  `json:"description" required:"true"`
	commentity.BKAdditional `json:",inline"`
}

// ClusterOperationLogsSearch 封装集群操作查询请求
type ClusterOperationLogsSearch struct {
	K8sClusterName string `json:"k8sClusterName" required:"true"`
	ClusterName    string `json:"clusterName" required:"true"`
	NameSpace      string `json:"namespace" required:"true"`
}

// CreateClusterOperationLogRequest 创建集群操作记录的请求
type CreateClusterOperationLogRequest struct {
	TicketID                uint64 `json:"ticketId" binding:"required"`
	ClusterName             string `json:"clusterName" binding:"required"`
	K8sClusterName          string `json:"k8sClusterName" binding:"required"`
	NameSpace               string `json:"nameSpace" binding:"required"`
	RequestType             string `json:"requestType" binding:"required"`
	commentity.BKAdditional `json:",inline"`
}
