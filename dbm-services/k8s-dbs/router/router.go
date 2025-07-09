/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License");
 * you may not use this file except in compliance with the License.
 *
 * You may obtain a copy of the License at
 * https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Package router 定义路由规则
package router

import (
	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"k8s-dbs/common/api"
	"k8s-dbs/core/provider"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	"log"
	"log/slog"

	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

const basePath = "/v4/dbs"

// Router 定义 Router
type Router struct {
	Engine *gin.Engine
}

// Run 启动 HTTP Server
func (r *Router) Run(addr string) {
	if err := r.Engine.Run(addr); err != nil {
		log.Fatalf("Failed to run server: %v", err)
	}
}

// NewRouter 创建并初始化 Router
func NewRouter(db *gorm.DB) *Router {
	router := gin.Default()

	// setup trace
	trace.Setup()
	// apm: add otlgin middleware
	router.Use(otelgin.Middleware("k8s_dbs"))
	// apm: add prom metrics middleware
	metric.NewPrometheus("").Use(router)

	router.GET(basePath+api.HealthCheckURL, api.HealthCheck)

	buildClusterRouter(db, router)

	buildComponentRouter(db, router)

	buildMetaRouter(db, router)

	buildK8sClusterRouter(db, router)

	buildAddonRouter(db, router)

	return &Router{Engine: router}
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
	clusterMetaDbAccess := metadbaccess.NewCrdClusterDbAccess(db)
	addonMetaDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := metadbaccess.NewK8sCrdClusterTagDbAccess(db)
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	clusterMetaProvider := metaprovider.NewK8sCrdClusterProvider(clusterMetaDbAccess,
		addonMetaDbAccess, clusterTagDbAccess, k8sClusterConfigDbAccess)

	componentMetaDbAccess := metadbaccess.NewK8sCrdComponentAccess(db)
	componentMetaProvider := metaprovider.NewK8sCrdComponentProvider(componentMetaDbAccess)

	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)

	requestRecordDbAccess := metadbaccess.NewClusterRequestRecordDbAccess(db)
	requestRecordProvider := metaprovider.NewClusterRequestRecordProvider(requestRecordDbAccess)

	clusterReleaseDbAccess := metadbaccess.NewAddonClusterReleaseDbAccess(db)
	clusterReleaseProvider := metaprovider.NewAddonClusterReleaseProvider(clusterReleaseDbAccess)

	helmRepoDbAccess := metadbaccess.NewAddonClusterHelmRepoDbAccess(db)
	helmRepoProvider := metaprovider.NewAddonClusterHelmRepoProvider(helmRepoDbAccess)

	addonMetaProvider := metaprovider.NewK8sCrdStorageAddonProvider(addonMetaDbAccess)

	clusterTagProvider := metaprovider.NewK8sCrdClusterTagProvider(clusterTagDbAccess)

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

// BuildClusterProvider 构建 ClusterProvider
func BuildClusterProvider(db *gorm.DB) *provider.ClusterProvider {
	coreAPIProviders, err := buildCoreAPIProviders(db)
	if err != nil {
		slog.Error("build common providers error", "error", err)
		panic(err)
	}
	clusterProviderBuilder := provider.ClusterProviderBuilder{}
	clusterProvider, err := provider.NewClusterProvider(
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

// BuildOpsRequestProvider 构建 OpsRequestProvider
func BuildOpsRequestProvider(db *gorm.DB, clusterProvider *provider.ClusterProvider) *provider.OpsRequestProvider {
	coreAPIProviders, err := buildCoreAPIProviders(db)
	if err != nil {
		slog.Error("build common providers error", "error", err)
		panic(err)
	}

	opsRequestMetaDbAccess := metadbaccess.NewK8sCrdOpsRequestDbAccess(db)
	opsRequestMetaProvider := metaprovider.NewK8sCrdOpsRequestProvider(opsRequestMetaDbAccess)
	opsRequestProviderBuilder := provider.OpsRequestProviderBuilder{}

	opsReqProvider, err := provider.NewOpsReqProvider(
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
