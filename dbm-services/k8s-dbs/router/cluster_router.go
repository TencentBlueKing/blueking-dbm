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
	routerhelper "k8s-dbs/router/helper"
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
		clusterGroup.POST("/partial_upgrade", clusterController.PartialUpdateCluster)
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
	clusterProvider := BuildClusterProvider(db)
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
	RegisterAPIRouterBuilder(BuildClusterRouter)
}

// BuildClusterProvider 构建 ClusterProvider
func BuildClusterProvider(db *gorm.DB) *coreprovider.ClusterProvider {
	coreAPIProviders, err := buildCoreAPIProviders(db)
	if err != nil {
		slog.Error("build common providers error", "error", err)
		panic(err)
	}
	clusterProviderBuilder := coreprovider.ClusterProviderBuilder{}
	clusterProvider, err := coreprovider.NewClusterProvider(
		clusterProviderBuilder.WithClusterMeta(coreAPIProviders.ClusterMetaProvider),
		clusterProviderBuilder.WithComponentMeta(coreAPIProviders.ComponentMetaProvider),
		clusterProviderBuilder.WithClusterConfigMeta(coreAPIProviders.ClusterConfigProvider),
		clusterProviderBuilder.WithReqRecordMeta(coreAPIProviders.RequestRecordProvider),
		clusterProviderBuilder.WithClusterHelmRepoMeta(coreAPIProviders.HelmRepoProvider),
		clusterProviderBuilder.WithReleaseMeta(coreAPIProviders.ClusterReleaseProvider),
		clusterProviderBuilder.WithAddonMeta(coreAPIProviders.AddonMetaProvider),
		clusterProviderBuilder.WithClusterTagsMeta(coreAPIProviders.ClusterTagProvider),
	)
	if err != nil {
		slog.Error("failed to build cluster provider", "error", err)
		panic(err)
	}
	return clusterProvider
}

// CoreAPIProviders 封装 core api providers
type CoreAPIProviders struct {
	ClusterMetaProvider    metaprovider.K8sCrdClusterProvider
	ComponentMetaProvider  metaprovider.K8sCrdComponentProvider
	ClusterConfigProvider  metaprovider.K8sClusterConfigProvider
	RequestRecordProvider  metaprovider.ClusterRequestRecordProvider
	ClusterReleaseProvider metaprovider.AddonClusterReleaseProvider
	HelmRepoProvider       metaprovider.AddonClusterHelmRepoProvider
	AddonMetaProvider      metaprovider.K8sCrdStorageAddonProvider
	ClusterTagProvider     metaprovider.K8sCrdClusterTagProvider
}

// buildCoreAPIProviders 构建 core api providers
func buildCoreAPIProviders(db *gorm.DB) (*CoreAPIProviders, error) {
	clusterMetaProvider := routerhelper.BuildClusterMetaProvider(db)
	componentMetaDbAccess := metadbaccess.NewK8sCrdComponentAccess(db)
	componentMetaProvider := metaprovider.NewK8sCrdComponentProvider(componentMetaDbAccess)

	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(metadbaccess.NewK8sClusterConfigDbAccess(db))

	requestRecordDbAccess := metadbaccess.NewClusterRequestRecordDbAccess(db)
	requestRecordProvider := metaprovider.NewClusterRequestRecordProvider(requestRecordDbAccess)

	clusterReleaseDbAccess := metadbaccess.NewAddonClusterReleaseDbAccess(db)
	clusterReleaseProvider := metaprovider.NewAddonClusterReleaseProvider(clusterReleaseDbAccess)

	helmRepoDbAccess := metadbaccess.NewAddonClusterHelmRepoDbAccess(db)
	helmRepoProvider := metaprovider.NewAddonClusterHelmRepoProvider(helmRepoDbAccess)

	addonMetaProvider := metaprovider.NewK8sCrdStorageAddonProvider(metadbaccess.NewK8sCrdStorageAddonDbAccess(db))

	clusterTagProvider := metaprovider.NewK8sCrdClusterTagProvider(metadbaccess.NewK8sCrdClusterTagDbAccess(db))

	return &CoreAPIProviders{
		ClusterMetaProvider:    clusterMetaProvider,
		ComponentMetaProvider:  componentMetaProvider,
		ClusterConfigProvider:  k8sClusterConfigProvider,
		RequestRecordProvider:  requestRecordProvider,
		ClusterReleaseProvider: clusterReleaseProvider,
		HelmRepoProvider:       helmRepoProvider,
		AddonMetaProvider:      addonMetaProvider,
		ClusterTagProvider:     clusterTagProvider,
	}, nil
}

// BuildOpsRequestProvider 构建 OpsRequestProvider
func BuildOpsRequestProvider(
	db *gorm.DB,
	clusterProvider *coreprovider.ClusterProvider,
) *coreprovider.OpsRequestProvider {
	coreAPIProviders, err := buildCoreAPIProviders(db)
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
