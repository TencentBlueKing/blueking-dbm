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

// addon 列表默认拉取行数
const DefaultAddonsFetchSizeStr = "50"
const DefaultAddonsFetchSize = 50
const MaxAddonsFetchSize = 100

const (
	TbK8sCrdStorageaddon        = "tb_k8s_crd_storageaddon"
	TbK8sCrdClusterdefinition   = "tb_k8s_crd_clusterdefinition"
	TbK8sCrdComponentdefinition = "tb_k8s_crd_componentdefinition"
	TbK8sCrdComponentversion    = "tb_k8s_crd_componentversion"
	TbK8sCrdCluster             = "tb_k8s_crd_cluster"
	TbK8sCrdComponent           = "tb_k8s_crd_component"
	TbK8sCrdOpsrequest          = "tb_k8s_crd_opsrequest"
	TbK8sClusterConfig          = "tb_k8s_cluster_config"
	TbClusterRequestRecord      = "tb_cluster_request_record"
	TbK8sClusterService         = "tb_k8s_cluster_service"
)

// MySQLTestURL mysql connection credentials for test
const (
	MySQLTestURL = "root:root@tcp(localhost:3306)/bkbase_dbs?charset=utf8mb4&parseTime=True&loc=Local"
)
