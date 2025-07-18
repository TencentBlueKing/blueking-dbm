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

// ClusterQueryParams cluster 元数据查询参数
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
	Status              string `gorm:"column:status" json:"status"`
	CreatedBy           string `gorm:"column:created_by" json:"createdBy"`
	UpdatedBy           string `gorm:"column:updated_by" json:"updatedBy"`
}

// ClusterRequestQueryParams cluster 操作元数据查询参数
type ClusterRequestQueryParams struct {
	ID             uint64 `gorm:"column:id" json:"id"`
	RequestID      string `gorm:"column:request_id" json:"requestId"`
	K8sClusterName string `gorm:"column:k8s_cluster_name" json:"k8sClusterName"`
	ClusterName    string `gorm:"column:cluster_name" json:"clusterName"`
	NameSpace      string `gorm:"column:namespace" json:"namespace"`
	RequestType    string `gorm:"column:request_type" json:"requestType"`
	RequestParams  string `gorm:"column:request_params" json:"requestParams"`
	CreatedBy      string `gorm:"column:created_by" json:"createdBy"`
	UpdatedBy      string `gorm:"column:updated_by" json:"updatedBy"`
}

// AddonQueryParams addon 插件元数据查询参数
type AddonQueryParams struct {
	ID                   uint64 `gorm:"column:id" json:"id"`
	AddonName            string `gorm:"column:addon_name" json:"addonName"`
	AddonCategory        string `gorm:"column:addon_category" json:"addonCategory"`
	AddonType            string `gorm:"column:addon_type" json:"addonType"`
	AddonVersion         string `gorm:"column:addon_version" json:"addonVersion"`
	Topologies           string `gorm:"column:topologies" json:"topologies"`
	RecommendedVersion   string `gorm:"column:recommended_version" json:"recommendedVersion"`
	SupportedVersions    string `gorm:"column:supported_versions" json:"supportedVersions"`
	RecommendedAcVersion string `gorm:"column:recommended_addoncluster_version" json:"recommendedAcVersion"`
	SupportedAcVersions  string `gorm:"column:supported_addoncluster_versions" json:"supportedAcVersions"`
	Releases             string `gorm:"column:releases" json:"releases"`
	Active               bool   `gorm:"column:active" json:"active"`
	CreatedBy            string `gorm:"size:50;not null;column:created_by" json:"createdBy"`
	UpdatedBy            string `gorm:"size:50;not null;column:updated_by" json:"updatedBy"`
}

// K8sClusterAddonQueryParams K8s 集群插件元数据查询参数
type K8sClusterAddonQueryParams struct {
	ID             uint64 `gorm:"column:id" json:"id"`
	AddonID        uint64 `gorm:"column:addon_id" json:"addonId"`
	K8sClusterName string `gorm:"column:k8s_cluster_name;" json:"k8sClusterName"`
	CreatedBy      string `gorm:"column:created_by" json:"createdBy"`
	UpdatedBy      string `gorm:"column:updated_by" json:"updatedBy"`
}

// HelmRepoQueryParams helm 仓库查询参数
type HelmRepoQueryParams struct {
	ID             int64  `gorm:"column:id" json:"id"`
	RepoName       string `gorm:"column:repo_name" json:"repoName"`
	RepoRepository string `gorm:"column:repo_repository" json:"repoRepository"`
	RepoUsername   string `gorm:"column:repo_username" json:"repoUsername"`
	RepoPassword   string `gorm:"column:repo_password" json:"repoPassword"`
	ChartName      string `gorm:"column:chart_name" json:"chartName"`
	ChartVersion   string `gorm:"column:chart_version" json:"chartVersion"`
	CreatedBy      string `gorm:"column:created_by" json:"createdBy"`
	UpdatedBy      string `gorm:"column:updated_by" json:"updatedBy"`
}

// ClusterReleaseQueryParams cluster release 元数据查询参数
type ClusterReleaseQueryParams struct {
	ID                 int64  `gorm:"column:id" json:"id"`
	RepoName           string `gorm:"column:repo_name" json:"repoName"`
	RepoRepository     string `gorm:"column:repo_repository" json:"repoRepository"`
	ChartVersion       string `gorm:"column:chart_version" json:"chartVersion"`
	ChartName          string `gorm:"column:chart_name" json:"chartName"`
	Namespace          string `gorm:"column:namespace" json:"namespace"`
	K8sClusterConfigID uint64 `gorm:"column:k8s_cluster_config_id" json:"k8sClusterConfigId"`
	ReleaseName        string `gorm:"column:release_name" json:"releaseName"`
	ChartValues        string `gorm:"column:chart_values" json:"chartValues"`
	CreatedBy          string `gorm:"column:created_by" json:"createdBy"`
	UpdatedBy          string `gorm:"column:updated_by" json:"updatedBy"`
}

// RegionQueryParams region 元数据查询参数
type RegionQueryParams struct {
	IsPublic   bool   `gorm:"type:tinyint(1);not null;default:1;column:is_public" json:"isPublic"`
	RegionName string `gorm:"column:region_name;type:varchar(32);not null" json:"regionName"`
	RegionCode string `gorm:"column:region_code;type:varchar(32);not null" json:"regionCode"`
	Provider   string `gorm:"column:provider;type:varchar(32);not null" json:"provider"`
}

// AddonVersionQueryParams addon 版本查询参数
type AddonVersionQueryParams struct {
	AddonCategory string `gorm:"column:addon_category" json:"addonCategory"`
	AddonType     string `gorm:"column:addon_type" json:"addonType"`
}

// AddonTopologyQueryParams addon topology 查询参数
type AddonTopologyQueryParams struct {
	AddonCategory string `gorm:"column:addon_category" json:"addonCategory"`
	AddonType     string `gorm:"column:addon_type" json:"addonType"`
	AddonVersion  string `gorm:"column:addon_version" json:"addonVersion"`
	TopologyName  string `gorm:"column:topology_name" json:"topologyName"`
}
