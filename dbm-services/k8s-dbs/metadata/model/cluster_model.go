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

package model

import (
	commtypes "k8s-dbs/common/types"
	"k8s-dbs/metadata/constant"
)

// K8sCrdClusterModel represents the database model of cluster
type K8sCrdClusterModel struct {
	ID                  uint64                 `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	AddonID             uint64                 `gorm:"not null;column:addon_id" json:"addonId"`
	AddonClusterVersion string                 `gorm:"size:32;column:addoncluster_version" json:"addonClusterVersion"`
	ServiceVersion      string                 `gorm:"size:32;column:service_version" json:"serviceVersion"`
	TopoName            string                 `gorm:"size:32;column:topo_name" json:"topoName"`
	TerminationPolicy   string                 `gorm:"size:32;column:termination_policy" json:"terminationPolicy"`
	K8sClusterConfigID  uint64                 `gorm:"not null;column:k8s_cluster_config_id" json:"k8sClusterConfigId"`
	RequestID           string                 `gorm:"not null;column:request_id" json:"requestId"`
	ClusterName         string                 `gorm:"size:32;not null;column:cluster_name" json:"clusterName"`
	ClusterAlias        string                 `gorm:"size:32;not null;column:cluster_alias" json:"clusterAlias"`
	Namespace           string                 `gorm:"size:32;not null;column:namespace" json:"namespace"`
	BkBizID             uint64                 `gorm:"not null;column:bk_biz_id" json:"bkBizId"`
	BkBizName           string                 `gorm:"size:128;not null;column:bk_biz_name" json:"bkBizName"`
	BkAppAbbr           string                 `gorm:"size:128;not null;column:bk_app_abbr" json:"bkAppAbbr"`
	BkAppCode           string                 `gorm:"size:128;not null;column:bk_app_code" json:"bkAppCode"`
	Status              string                 `gorm:"size:32;column:status" json:"status"`
	Description         string                 `gorm:"size:100;column:description" json:"description"`
	CreatedBy           string                 `gorm:"size:50;not null;column:created_by" json:"createdBy"`
	CreatedAt           commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"createdAt"` //nolint:lll
	UpdatedBy           string                 `gorm:"size:50;not null;column:updated_by" json:"updatedBy"`
	UpdatedAt           commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updatedAt"` //nolint:lll
}

// TableName 获取 model 对应的数据库表名
func (K8sCrdClusterModel) TableName() string {
	return constant.TbK8sCrdCluster
}
