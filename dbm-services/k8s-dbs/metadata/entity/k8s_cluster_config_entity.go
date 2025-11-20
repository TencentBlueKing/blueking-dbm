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

package entity

import commtypes "k8s-dbs/common/types"

// K8sClusterConfigEntity k8s cluster config entity 定义
type K8sClusterConfigEntity struct {
	ID            uint64 `json:"id"`
	ClusterName   string `json:"clusterName"`
	APIServerURL  string `json:"apiServerUrl"`
	CACert        string `json:"caCert"`
	ClientCert    string `json:"clientCert"`
	ClientKey     string `json:"clientKey"`
	Token         string `json:"token"`
	Username      string `json:"username"`
	Password      string `json:"password"`
	*RegionEntity `json:",inline"`
	Active        bool                   `json:"active"`
	Description   string                 `json:"description"`
	CreatedBy     string                 `json:"createdBy"`
	CreatedAt     commtypes.JSONDatetime `json:"createdAt"`
	UpdatedBy     string                 `json:"updatedBy"`
	UpdatedAt     commtypes.JSONDatetime `json:"updatedAt"`
}

// RegionEntity 区域信息 entity
type RegionEntity struct {
	IsPublic    bool   `json:"isPublic"`
	ClusterName string `json:"clusterName"`
	RegionName  string `json:"regionName"`
	RegionCode  string `json:"regionCode"`
	Provider    string `json:"provider"`
}
