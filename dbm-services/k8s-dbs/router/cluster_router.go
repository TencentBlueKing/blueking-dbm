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
	"k8s-dbs/core/provider"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

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
		clusterGroup.POST("/delete", clusterController.DeleteCluster)
		clusterGroup.POST("/describe", clusterController.DescribeCluster)
		clusterGroup.POST("/status", clusterController.GetClusterStatus)
		clusterGroup.POST("/event", clusterController.GetClusterEvent)

	}

	componentGroup := router.Group(basePath + "/component")
	{
		componentGroup.POST("/describe", clusterController.DescribeComponent)
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

// buildService 总路由规则构建
func buildService(db *gorm.DB) (*provider.ClusterProvider, *provider.OpsRequestProvider) {
	clusterDbAccess := metadbaccess.NewCrdClusterDbAccess(db)
	clusterDefinitionDbAccess := metadbaccess.NewK8sCrdClusterDefinitionDbAccess(db)
	componentDbAccess := metadbaccess.NewK8sCrdComponentAccess(db)
	componentDefinitionDbAccess := metadbaccess.NewK8sCrdCmpdDbAccess(db)
	componentVersionDbAccess := metadbaccess.NewK8sCrdCmpvDbAccess(db)
	opsReqDbAccess := metadbaccess.NewK8sCrdOpsRequestDbAccess(db)
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	requestRecordDbAccess := metadbaccess.NewClusterRequestRecordDbAccess(db)
	clusterReleaseDbAccess := metadbaccess.NewAddonClusterReleaseDbAccess(db)
	helmRepoDbAccess := metadbaccess.NewAddonClusterHelmRepoDbAccess(db)

	clusterProvider := metaprovider.NewK8sCrdClusterProvider(clusterDbAccess)
	clusterDefinitionProvider := metaprovider.NewK8sCrdClusterDefinitionProvider(clusterDefinitionDbAccess)
	componentProvider := metaprovider.NewK8sCrdComponentProvider(componentDbAccess)
	componentDefinitionProvider := metaprovider.NewK8sCrdCmpdProvider(componentDefinitionDbAccess)
	componentVersionProvider := metaprovider.NewK8sCrdCmpvProvider(componentVersionDbAccess)
	opsReqProvider := metaprovider.NewK8sCrdOpsRequestProvider(opsReqDbAccess)
	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	requestRecordProvider := metaprovider.NewClusterRequestRecordProvider(requestRecordDbAccess)
	clusterReleaseProvider := metaprovider.NewAddonClusterReleaseProvider(clusterReleaseDbAccess)
	helmRepoMetaProvider := metaprovider.NewAddonClusterHelmRepoProvider(helmRepoDbAccess)

	clusterService, err := provider.NewClusterProviderBuilder().
		WithClusterMetaProvider(clusterProvider).
		WithComponentMetaProvider(componentProvider).
		WithCdMetaProvider(clusterDefinitionProvider).
		WithCmpdMetaProvider(componentDefinitionProvider).
		WithCmpvMetaProvider(componentVersionProvider).
		WithClusterConfigMetaProvider(k8sClusterConfigProvider).
		WithReqRecordProvider(requestRecordProvider).
		WithClusterHelmRepoProvider(helmRepoMetaProvider).
		WithReleaseMetaProvider(clusterReleaseProvider).Build()
	if err != nil {
		slog.Error("build cluster provider error", "error", err.Error())
		panic(err)
	}

	opsReqService, err := provider.NewOpsReqProviderBuilder().
		WithopsRequestMetaProvider(opsReqProvider).
		WithClusterMetaProvider(clusterProvider).
		WithClusterConfigMetaProvider(k8sClusterConfigProvider).
		WithReqRecordProvider(requestRecordProvider).
		WithReleaseMetaProvider(clusterReleaseProvider).
		WithClusterProvider(clusterService).Build()
	if err != nil {
		slog.Error("build ops request provider error", "error", err.Error())
		panic(err)
	}

	return clusterService, opsReqService
}

// initClusterController 初始化 ClusterController
func initClusterController(db *gorm.DB) *controller.ClusterController {
	return controller.NewClusterController(buildService(db))
}
