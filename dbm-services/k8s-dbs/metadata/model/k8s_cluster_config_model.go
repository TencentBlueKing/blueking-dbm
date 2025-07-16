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
	"k8s-dbs/metadata/constant"
	"time"
)

// K8sClusterConfigModel represents the database model of cluster config
type K8sClusterConfigModel struct {
	ID           uint64    `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	ClusterName  string    `gorm:"column:cluster_name;type:varchar(255);not null" json:"clusterName"`
	APIServerURL string    `gorm:"column:api_server_url;type:varchar(255);not null" json:"apiServerUrl"`
	CACert       string    `gorm:"column:ca_cert;type:text" json:"caCert"`
	ClientCert   string    `gorm:"column:client_cert;type:text" json:"clientCert"`
	ClientKey    string    `gorm:"column:client_key;type:text" json:"clientKey"`
	Token        string    `gorm:"column:token;type:text" json:"token"`
	Username     string    `gorm:"column:username;type:varchar(255);" json:"username"`
	Password     string    `gorm:"column:password;type:varchar(255);" json:"password"`
	IsPublic     bool      `gorm:"type:tinyint(1);not null;default:1;column:is_public" json:"isPublic"`
	RegionName   string    `gorm:"column:region_name;type:varchar(32);not null" json:"regionName"`
	RegionCode   string    `gorm:"column:region_code;type:varchar(32);not null" json:"regionCode"`
	Provider     string    `gorm:"column:provider;type:varchar(32);not null" json:"provider"`
	Active       bool      `gorm:"type:tinyint(1);not null;default:1;column:active" json:"active"`
	Description  string    `gorm:"size:100;column:description" json:"description"`
	CreatedBy    string    `gorm:"size:50;not null;column:created_by" json:"createdBy"`
	CreatedAt    time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"createdAt"` //nolint:lll
	UpdatedBy    string    `gorm:"size:50;not null;column:updated_by" json:"updatedBy"`
	UpdatedAt    time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updatedAt"` //nolint:lll
}

// RegionModel 区域信息 model
type RegionModel struct {
	IsPublic   bool   `gorm:"type:tinyint(1);not null;default:1;column:is_public" json:"isPublic"`
	RegionName string `gorm:"column:region_name;type:varchar(32);not null" json:"regionName"`
	RegionCode string `gorm:"column:region_code;type:varchar(32);not null" json:"regionCode"`
	Provider   string `gorm:"column:provider;type:varchar(32);not null" json:"provider"`
}

// TableName 获取 model 对应的数据库表名
func (K8sClusterConfigModel) TableName() string {
	return constant.TbK8sClusterConfig
}
