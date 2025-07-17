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

package req

import commtypes "k8s-dbs/common/types"

// K8sClusterConfigReqVo represents the request data structure of k8sClusterConfig meta.
type K8sClusterConfigReqVo struct {
	ClusterName  string                 `json:"clusterName" binding:"required"`
	APIServerURL string                 `json:"apiServerUrl" binding:"required"`
	CACert       string                 `json:"caCert" binding:"required"`
	ClientCert   string                 `json:"clientCert" binding:"required"`
	ClientKey    string                 `json:"clientKey" binding:"required"`
	Token        string                 `json:"token" binding:"required"`
	Username     string                 `json:"username" binding:"required"`
	Password     string                 `json:"password" binding:"required"`
	Description  string                 `json:"description" binding:"required"`
	CreatedBy    string                 `json:"createdBy" binding:"required"`
	CreatedAt    commtypes.JSONDatetime `json:"createdAt"`
	UpdatedBy    string                 `json:"updatedBy"`
	UpdatedAt    commtypes.JSONDatetime `json:"updatedAt"`
}
