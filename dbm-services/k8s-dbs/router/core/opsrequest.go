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
	coreprovider "k8s-dbs/core/provider"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	routerutil "k8s-dbs/router/util"
	"log/slog"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// BuildOpsRequestRouter opsRequest 管理路由构建
func BuildOpsRequestRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	clusterController := initClusterController(db)
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

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildOpsRequestRouter)
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

	opsRequestMetaDbAccess := metadbaccess.GetOpsRequestDbAccess(db)
	opsRequestMetaProvider := metaprovider.GetK8sCrdOpsRequestProvider(opsRequestMetaDbAccess)
	opsRequestProviderBuilder := coreprovider.OpsRequestProviderBuilder{}

	opsReqProvider, err := coreprovider.NewOpsReqProvider(
		opsRequestProviderBuilder.WithOpsRequestMeta(opsRequestMetaProvider),
		opsRequestProviderBuilder.WithClusterMeta(coreAPIProviders.ClusterMetaProvider),
		opsRequestProviderBuilder.WithClusterConfigMeta(coreAPIProviders.ClusterConfigProvider),
		opsRequestProviderBuilder.WithReqRecordMeta(coreAPIProviders.RequestRecordProvider),
		opsRequestProviderBuilder.WithReleaseMeta(coreAPIProviders.ClusterReleaseProvider),
		opsRequestProviderBuilder.WithClusterProvider(clusterProvider),
		opsRequestProviderBuilder.WithDbmAPIService(coreAPIProviders.DbmAPIService),
	)

	if err != nil {
		slog.Error("build ops request provider error", "error", err)
		panic(err)
	}

	return opsReqProvider
}
