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

package util

import (
	"k8s-dbs/common/api"
	coreprovider "k8s-dbs/core/provider"
	"k8s-dbs/infrastructure/thirdapi"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	"github.com/gin-gonic/gin"

	"gorm.io/gorm"
)

// BuildClusterMetaProvider 构建 K8sCrdClusterProviderImpl
func BuildClusterMetaProvider(db *gorm.DB) metaprovider.K8sCrdClusterProvider {
	clusterMetaDbAccess := metadbaccess.GetClusterDbAccess(db)
	addonMetaDbAccess := metadbaccess.GetStorageAddonDbAccess(db)
	clusterTagDbAccess := metadbaccess.GetClusterTagDbAccess(db)
	k8sClusterConfigDbAccess := metadbaccess.GetK8sClusterConfigDbAccess(db)
	clusterTopologyDbAccess := metadbaccess.GetAddonTopologyDbAccess(db)
	addonTypeDbAccess := metadbaccess.GetAddonTypeDbAccess(db)

	clusterMetaProviderBuilder := metaprovider.K8sCrdClusterProviderBuilder{}
	clusterMetaProvider := metaprovider.GetK8sCrdClusterProvider(
		clusterMetaProviderBuilder.WithClusterDbAccess(clusterMetaDbAccess),
		clusterMetaProviderBuilder.WithAddonDbAccess(addonMetaDbAccess),
		clusterMetaProviderBuilder.WithK8sClusterConfigDbAccess(k8sClusterConfigDbAccess),
		clusterMetaProviderBuilder.WithClusterTagDbAccess(clusterTagDbAccess),
		clusterMetaProviderBuilder.WithAddonTopologyDbAccess(clusterTopologyDbAccess),
		clusterMetaProviderBuilder.WithAddonTypeDbAccess(addonTypeDbAccess),
	)
	return clusterMetaProvider
}

// BuildComponentProvider 构建 ComponentController
func BuildComponentProvider(db *gorm.DB) *coreprovider.ComponentProvider {
	k8sClusterConfigDbAccess := metadbaccess.GetK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := metaprovider.GetK8sClusterConfigProvider(k8sClusterConfigDbAccess)

	clusterMetaDbAccess := metadbaccess.GetClusterDbAccess(db)
	addonMetaDbAccess := metadbaccess.GetStorageAddonDbAccess(db)
	clusterTagDbAccess := metadbaccess.GetClusterTagDbAccess(db)
	clusterTopologyDbAccess := metadbaccess.GetAddonTopologyDbAccess(db)
	addonTypeDbAccess := metadbaccess.GetAddonTypeDbAccess(db)

	clusterProviderBuilder := metaprovider.K8sCrdClusterProviderBuilder{}
	clusterMetaProvider := metaprovider.GetK8sCrdClusterProvider(
		clusterProviderBuilder.WithClusterDbAccess(clusterMetaDbAccess),
		clusterProviderBuilder.WithAddonDbAccess(addonMetaDbAccess),
		clusterProviderBuilder.WithK8sClusterConfigDbAccess(k8sClusterConfigDbAccess),
		clusterProviderBuilder.WithClusterTagDbAccess(clusterTagDbAccess),
		clusterProviderBuilder.WithAddonTopologyDbAccess(clusterTopologyDbAccess),
		clusterProviderBuilder.WithAddonTypeDbAccess(addonTypeDbAccess),
	)

	return coreprovider.NewComponentProvider(k8sClusterConfigProvider, clusterMetaProvider)
}

// BuildClusterProvider 构建 ClusterProvider
func BuildClusterProvider(db *gorm.DB) *coreprovider.ClusterProvider {
	coreAPIProviders, err := BuildCoreAPIProviders(db)
	if err != nil {
		slog.Error("build common providers error", "error", err)
		panic(err)
	}
	clusterServiceDbAccess := metadbaccess.GetClusterServiceDbAccess(db)
	clusterServiceProvider := metaprovider.GetK8sClusterServiceProvider(clusterServiceDbAccess)
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
		clusterProviderBuilder.WithDbmAPIService(coreAPIProviders.DbmAPIService),
		clusterProviderBuilder.WithClusterServiceMeta(clusterServiceProvider),
	)
	if err != nil {
		slog.Error("failed to build cluster provider", "error", err)
		panic(err)
	}
	return clusterProvider
}

// BuildK8sCrdOpsRequestProvider 构建 K8sCrdOpsRequestProvider
func BuildK8sCrdOpsRequestProvider(db *gorm.DB) metaprovider.K8sCrdOpsRequestProvider {
	crdOpsRequestDbAccess := metadbaccess.GetOpsRequestDbAccess(db)
	opsRequestMetaProvider := metaprovider.GetK8sCrdOpsRequestProvider(crdOpsRequestDbAccess)
	return opsRequestMetaProvider
}

// BuildK8sClusterConfigProvider 构建 K8sClusterConfigProvider
func BuildK8sClusterConfigProvider(db *gorm.DB) metaprovider.K8sClusterConfigProvider {
	k8sClusterConfigDbAccess := metadbaccess.GetK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := metaprovider.GetK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	return k8sClusterConfigProvider
}

// BuildCoreAPIProviders 构建 core api providers
func BuildCoreAPIProviders(db *gorm.DB) (*CoreAPIProviders, error) {
	clusterMetaProvider := BuildClusterMetaProvider(db)
	componentMetaDbAccess := metadbaccess.GetComponentDbAccess(db)
	componentMetaProvider := metaprovider.GetK8sCrdComponentProvider(componentMetaDbAccess)

	k8sClusterConfigProvider := metaprovider.GetK8sClusterConfigProvider(metadbaccess.GetK8sClusterConfigDbAccess(db))

	requestRecordDbAccess := metadbaccess.GetClusterRequestDbAccess(db)
	requestRecordProvider := metaprovider.GetClusterRequestRecordProvider(requestRecordDbAccess)

	clusterReleaseDbAccess := metadbaccess.GetAcReleaseDbAccess(db)
	clusterReleaseProvider := metaprovider.GetAddonClusterReleaseProvider(clusterReleaseDbAccess)

	helmRepoDbAccess := metadbaccess.GetAcHelmRepoDbAccess(db)
	helmRepoProvider := metaprovider.GetAddonClusterHelmRepoProvider(helmRepoDbAccess)

	addonMetaProvider := metaprovider.GetK8sCrdStorageAddonProvider(metadbaccess.GetStorageAddonDbAccess(db))

	clusterTagProvider := metaprovider.GetK8sCrdClusterTagProvider(metadbaccess.GetClusterTagDbAccess(db))

	dbmAPIService := thirdapi.NewDbmAPIService()
	return &CoreAPIProviders{
		ClusterMetaProvider:    clusterMetaProvider,
		ComponentMetaProvider:  componentMetaProvider,
		ClusterConfigProvider:  k8sClusterConfigProvider,
		RequestRecordProvider:  requestRecordProvider,
		ClusterReleaseProvider: clusterReleaseProvider,
		HelmRepoProvider:       helmRepoProvider,
		AddonMetaProvider:      addonMetaProvider,
		ClusterTagProvider:     clusterTagProvider,
		DbmAPIService:          dbmAPIService,
	}, nil
}

// BuildOpsRequestProvider 构建 OpsRequestProvider
func BuildOpsRequestProvider(
	db *gorm.DB,
) *coreprovider.OpsRequestProvider {
	coreAPIProviders, err := BuildCoreAPIProviders(db)
	if err != nil {
		slog.Error("build common providers error", "error", err)
		panic(err)
	}
	clusterProvider := BuildClusterProvider(db)
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
	DbmAPIService          *thirdapi.DbmAPIService
}

// CustomRouterBuilder 自定义 Router 构建函数
type CustomRouterBuilder func(db *gorm.DB, engine *gin.RouterGroup)

var CustomRouterBuilders []CustomRouterBuilder

// RegisterAPIRouterBuilder 注册 CustomRouterBuilder
func RegisterAPIRouterBuilder(builder CustomRouterBuilder) {
	CustomRouterBuilders = append(CustomRouterBuilders, builder)
}

// BuildAPIRouters 元数据路由构建
func BuildAPIRouters(db *gorm.DB, engine *gin.RouterGroup) {
	for _, builder := range CustomRouterBuilders {
		builder(db, engine)
	}
}

// BuildHealthRouter 健康检查路由构建
func BuildHealthRouter(router *gin.RouterGroup) gin.IRoutes {
	return router.GET(api.HealthCheckURL, api.HealthCheck)
}
