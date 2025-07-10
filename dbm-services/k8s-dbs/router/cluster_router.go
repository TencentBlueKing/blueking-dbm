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

package router

import (
	"k8s-dbs/core/api/controller"
	coreprovider "k8s-dbs/core/provider"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// buildClusterRouter cluster 管理路由构建
func buildClusterRouter(db *gorm.DB, router *gin.Engine) {
	clusterController := initClusterController(db)
	clusterGroup := router.Group(basePath + "/cluster")
	{

		clusterGroup.POST("/create", clusterController.CreateCluster)
		clusterGroup.POST("/update", clusterController.UpdateCluster)
		clusterGroup.POST("/partial_upgrade", clusterController.PartialUpdateCluster)
		clusterGroup.POST("/delete", clusterController.DeleteCluster)
		clusterGroup.POST("/describe", clusterController.DescribeCluster)
		clusterGroup.POST("/service/describe", clusterController.GetClusterLinks)
		clusterGroup.POST("/status", clusterController.GetClusterStatus)
		clusterGroup.POST("/event", clusterController.GetClusterEvent)

	}

	opsRequestGroup := router.Group(basePath + "/opsRequest")
	{
		opsRequestGroup.POST("/vscaling", clusterController.VerticalScaling)
		opsRequestGroup.POST("/hscaling", clusterController.HorizontalScaling)
		opsRequestGroup.POST("/start", clusterController.StartCluster)
		opsRequestGroup.POST("/stop", clusterController.StopCluster)
		opsRequestGroup.POST("/restart", clusterController.RestartCluster)
		opsRequestGroup.POST("/upgrade", clusterController.UpgradeCluster)
		opsRequestGroup.POST("/vexpansion", clusterController.VolumeExpansion)
		opsRequestGroup.POST("/expose", clusterController.ExposeCluster)
		opsRequestGroup.POST("/describe", clusterController.DescribeOpsRequest)
		opsRequestGroup.POST("/status", clusterController.GetOpsRequestStatus)
	}
}

// initClusterController 初始化 ClusterController
func initClusterController(db *gorm.DB) *controller.ClusterController {
	clusterProvider := BuildClusterProvider(db)
	opsRequestProvider := BuildOpsRequestProvider(db, clusterProvider)
	clusterMetaDbAccess := metadbaccess.NewCrdClusterDbAccess(db)
	addonMetaDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := metadbaccess.NewK8sCrdClusterTagDbAccess(db)
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	clusterMetaProvider := metaprovider.NewK8sCrdClusterProvider(clusterMetaDbAccess,
		addonMetaDbAccess, clusterTagDbAccess, k8sClusterConfigDbAccess)
	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	componentProvider := coreprovider.NewComponentProvider(k8sClusterConfigProvider)
	return controller.NewClusterController(clusterProvider,
		clusterMetaProvider, componentProvider, opsRequestProvider)
}
