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

import (
	"time"
)

// K8sCrdClusterEntity cluster entity 定义
type K8sCrdClusterEntity struct {
	ID                  uint64                   `json:"id"`
	AddonID             uint64                   `json:"addonId"`
	AddonClusterVersion string                   `json:"addonClusterVersion"`
	AddonInfo           K8sCrdStorageAddonEntity `json:"addonInfo"`
	TopoName            string                   `json:"topoName"`
	K8sClusterConfigID  uint64                   `json:"k8sClusterConfigId"`
	RequestID           string                   `json:"requestId"`
	ClusterName         string                   `json:"clusterName"`
	ClusterAlias        string                   `json:"clusterAlias"`
	Namespace           string                   `json:"namespace"`
	BkBizID             uint64                   `json:"bkBizId"`
	BkBizName           string                   `json:"bkBizName"`
	BkAppAbbr           string                   `json:"bkAppAbbr"`
	BkAppCode           string                   `json:"bkAppCode"`
	Status              string                   `json:"status"`
	Description         string                   `json:"description"`
	CreatedBy           string                   `json:"createdBy"`
	CreatedAt           time.Time                `json:"createdAt"`
	UpdatedBy           string                   `json:"updatedBy"`
	UpdatedAt           time.Time                `json:"updatedAt"`
}
