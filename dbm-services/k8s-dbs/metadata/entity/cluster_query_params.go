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

// ClusterQueryParams cluster 查询参数
type ClusterQueryParams struct {
	ID                  uint64 `gorm:"column:id"`
	AddonID             uint64 `gorm:"column:addon_id"`
	AddonClusterVersion string `gorm:"column:addoncluster_version"`
	TopoName            string `gorm:"column:topo_name" json:"topoName"`
	K8sClusterConfigID  uint64 `gorm:"column:k8s_cluster_config_id" json:"k8sClusterConfigId"`
	ClusterName         string `gorm:"column:cluster_name" json:"clusterName"`
	ClusterAlias        string `gorm:"column:cluster_alias" json:"clusterAlias"`
	Namespace           string `gorm:"column:namespace" json:"namespace"`
	BkBizID             uint64 `gorm:"column:bk_biz_id" json:"bkBizId"`
	BkBizName           string `gorm:"column:bk_biz_name" json:"bkBizName"`
	BkAppAbbr           string `gorm:"column:bk_app_abbr" json:"bkAppAbbr"`
	BkAppCode           string `gorm:"column:bk_app_code" json:"bkAppCode"`
}
