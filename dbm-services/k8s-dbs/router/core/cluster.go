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

package core

import (
	"k8s-dbs/core/api/controller"
	coreprovider "k8s-dbs/core/provider"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	routerutil "k8s-dbs/router/util"
	"log/slog"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// BuildClusterRouter cluster 管理路由构建
func BuildClusterRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	clusterController := initClusterController(db)
	clusterGroup := baseRouter.Group("/cluster")
	{

		clusterGroup.POST("/create", clusterController.CreateCluster)
		clusterGroup.POST("/update", clusterController.UpdateCluster)
		clusterGroup.POST("/partial_update", clusterController.PartialUpdateCluster)
		clusterGroup.POST("/delete", clusterController.DeleteCluster)
		clusterGroup.POST("/describe", clusterController.DescribeCluster)
		clusterGroup.GET("/services", clusterController.GetClusterService)
		clusterGroup.POST("/status", clusterController.GetClusterStatus)
		clusterGroup.POST("/event", clusterController.GetClusterEvent)

	}

	opsRequestGroup := baseRouter.Group("/opsRequest")
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
	clusterProvider := routerutil.BuildClusterProvider(db)
	opsRequestProvider := BuildOpsRequestProvider(db, clusterProvider)
	clusterMetaDbAccess := metadbaccess.NewCrdClusterDbAccess(db)
	addonMetaDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := metadbaccess.NewK8sCrdClusterTagDbAccess(db)
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	clusterTopologyDbAccess := metadbaccess.NewAddonTopologyDbAccess(db)
	clusterProviderBuilder := metaprovider.K8sCrdClusterProviderBuilder{}
	clusterMetaProvider, err := metaprovider.NewK8sCrdClusterProvider(
		clusterProviderBuilder.WithClusterDbAccess(clusterMetaDbAccess),
		clusterProviderBuilder.WithAddonDbAccess(addonMetaDbAccess),
		clusterProviderBuilder.WithK8sClusterConfigDbAccess(k8sClusterConfigDbAccess),
		clusterProviderBuilder.WithClusterTagDbAccess(clusterTagDbAccess),
		clusterProviderBuilder.WithAddonTopologyDbAccess(clusterTopologyDbAccess),
	)
	if err != nil {
		slog.Error("failed to build cluster meta provider", "error", err)
		panic(err)
	}
	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	componentProvider := coreprovider.NewComponentProvider(k8sClusterConfigProvider, clusterMetaProvider)
	return controller.NewClusterController(clusterProvider,
		clusterMetaProvider, componentProvider, opsRequestProvider)
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildClusterRouter)
}

// BuildOpsRequestProvider 构建 OpsRequestProvider
func BuildOpsRequestProvider(
	db *gorm.DB,
	clusterProvider *coreprovider.ClusterProvider,
) *coreprovider.OpsRequestProvider {
	coreAPIProviders, err := routerutil.BuildCoreAPIProviders(db)
	if err != nil {
		slog.Error("build common providers error", "error", err)
		panic(err)
	}

	opsRequestMetaDbAccess := metadbaccess.NewK8sCrdOpsRequestDbAccess(db)
	opsRequestMetaProvider := metaprovider.NewK8sCrdOpsRequestProvider(opsRequestMetaDbAccess)
	opsRequestProviderBuilder := coreprovider.OpsRequestProviderBuilder{}

	opsReqProvider, err := coreprovider.NewOpsReqProvider(
		opsRequestProviderBuilder.WithOpsRequestMeta(opsRequestMetaProvider),
		opsRequestProviderBuilder.WithClusterMeta(coreAPIProviders.ClusterMetaProvider),
		opsRequestProviderBuilder.WithClusterConfigMeta(coreAPIProviders.ClusterConfigProvider),
		opsRequestProviderBuilder.WithReqRecordMeta(coreAPIProviders.RequestRecordProvider),
		opsRequestProviderBuilder.WithReleaseMeta(coreAPIProviders.ClusterReleaseProvider),
		opsRequestProviderBuilder.WithClusterProvider(clusterProvider))

	if err != nil {
		slog.Error("build ops request provider error", "error", err)
		panic(err)
	}

	return opsReqProvider
}
