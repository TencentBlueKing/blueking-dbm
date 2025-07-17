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

// K8sCrdClusterTagModel 存储集群的标签信息表
type K8sCrdClusterTagModel struct {
	ID           uint64                 `gorm:"primaryKey;autoIncrement;comment:主键 id" json:"id"`
	CrdClusterID uint64                 `gorm:"not null;comment:关联 k8s_crd_cluster 主键 id" json:"crdClusterId"`
	ClusterTag   string                 `gorm:"type:varchar(32);default:'';comment:k8s 集群标签" json:"clusterTag"`
	Active       bool                   `gorm:"not null;default:1;comment:0:无效，1:有效" json:"active"`
	CreatedBy    string                 `gorm:"size:50;not null;column:created_by" json:"createdBy"`
	CreatedAt    commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"createdAt"` //nolint:lll
	UpdatedBy    string                 `gorm:"size:50;not null;column:updated_by" json:"updatedBy"`
	UpdatedAt    commtypes.JSONDatetime `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updatedAt"` //nolint:lll
}

// TableName 设置表名
func (K8sCrdClusterTagModel) TableName() string {
	return constant.TbK8sCrdClusterTag
}
