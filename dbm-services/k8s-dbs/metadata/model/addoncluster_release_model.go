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

// AddonClusterReleaseModel 对应 tb_addoncluster_release 表
type AddonClusterReleaseModel struct {
	ID                 int64                  `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	RepoName           string                 `gorm:"type:varchar(32);not null;column:repo_name" json:"repoName"`
	RepoRepository     string                 `gorm:"type:varchar(255);not null;column:repo_repository" json:"repoRepository"` //nolint:lll
	ChartVersion       string                 `gorm:"type:varchar(32);not null;column:chart_version" json:"chartVersion"`
	ChartName          string                 `gorm:"type:varchar(32);not null;column:chart_name" json:"chartName"`
	Namespace          string                 `gorm:"size:32;not null;column:namespace" json:"namespace"`
	K8sClusterConfigID uint64                 `gorm:"not null;column:k8s_cluster_config_id" json:"k8sClusterConfigId"`
	ReleaseName        string                 `gorm:"type:varchar(32);not null;column:release_name" json:"releaseName"`
	ChartValues        string                 `gorm:"type:text;not null;column:chart_values" json:"chartValues"`
	CreatedBy          string                 `gorm:"size:50;not null;column:created_by" json:"createdBy"`
	CreatedAt          commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"createdAt"` //nolint:lll
	UpdatedBy          string                 `gorm:"size:50;not null;column:updated_by" json:"updatedBy"`
	UpdatedAt          commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updatedAt"` //nolint:lll
}

// TableName 获取 model 对应的数据库表名
func (AddonClusterReleaseModel) TableName() string {
	return constant.TbAddonClusterRelease
}
