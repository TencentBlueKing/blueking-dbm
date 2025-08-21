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
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	"github.com/gin-gonic/gin"

	"gorm.io/gorm"
)

// BuildClusterMetaProvider 构建 K8sCrdClusterProviderImpl
func BuildClusterMetaProvider(db *gorm.DB) *metaprovider.K8sCrdClusterProviderImpl {
	clusterMetaDbAccess := metadbaccess.NewCrdClusterDbAccess(db)
	addonMetaDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := metadbaccess.NewK8sCrdClusterTagDbAccess(db)
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	clusterTopologyDbAccess := metadbaccess.NewAddonTopologyDbAccess(db)

	clusterMetaProviderBuilder := metaprovider.K8sCrdClusterProviderBuilder{}
	clusterMetaProvider, err := metaprovider.NewK8sCrdClusterProvider(
		clusterMetaProviderBuilder.WithClusterDbAccess(clusterMetaDbAccess),
		clusterMetaProviderBuilder.WithAddonDbAccess(addonMetaDbAccess),
		clusterMetaProviderBuilder.WithK8sClusterConfigDbAccess(k8sClusterConfigDbAccess),
		clusterMetaProviderBuilder.WithClusterTagDbAccess(clusterTagDbAccess),
		clusterMetaProviderBuilder.WithAddonTopologyDbAccess(clusterTopologyDbAccess),
	)
	if err != nil {
		slog.Error("failed to build cluster meta provider", "error", err)
		panic(err)
	}
	return clusterMetaProvider
}

// BuildClusterProvider 构建 ClusterProvider
func BuildClusterProvider(db *gorm.DB) *coreprovider.ClusterProvider {
	coreAPIProviders, err := BuildCoreAPIProviders(db)
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

// BuildCoreAPIProviders 构建 core api providers
func BuildCoreAPIProviders(db *gorm.DB) (*CoreAPIProviders, error) {
	clusterMetaProvider := BuildClusterMetaProvider(db)
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
