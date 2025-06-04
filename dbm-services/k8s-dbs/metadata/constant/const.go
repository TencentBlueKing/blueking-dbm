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

package constant

// DefaultFetchSizeStr 列表默认拉取行数
const DefaultFetchSizeStr = "50"
const DefaultFetchSize = 50
const MaxFetchSize = 100

const (
	TbK8sCrdStorageAddon        = "tb_k8s_crd_storageaddon"
	TbK8sCrdClusterDefinition   = "tb_k8s_crd_clusterdefinition"
	TbK8sCrdComponentDefinition = "tb_k8s_crd_componentdefinition"
	TbK8sCrdComponentVersion    = "tb_k8s_crd_componentversion"
	TbK8sCrdCluster             = "tb_k8s_crd_cluster"
	TbK8sCrdComponent           = "tb_k8s_crd_component"
	TbK8sCrdOpsRequest          = "tb_k8s_crd_opsrequest"
	TbK8sClusterConfig          = "tb_k8s_cluster_config"
	TbClusterRequestRecord      = "tb_cluster_request_record"
	TbK8sClusterService         = "tb_k8s_cluster_service"
	TbOperationDefinition       = "tb_operation_definition"
	TbComponentOperation        = "tb_component_operation"
	TbClusterOperation          = "tb_cluster_operation"
	TbAddonClusterRelease       = "tb_addoncluster_release"
	TbAddonClusterHelmRepo      = "tb_addoncluster_helm_repository"
	TbAddonHelmRepo             = "tb_addon_helm_repository"
)

// MySQLTestURL mysql connection credentials for test
const (
	MySQLTestURL = "root:TestPwd123@tcp(localhost:3306)/bkbase_dbs?charset=utf8mb4&parseTime=True&loc=Local"
)
