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

// Package router 定义路由规则
package router

import (
	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"k8s-dbs/common/api"
	"k8s-dbs/core/api/controller"
	"k8s-dbs/core/provider/clustermanage"
	"k8s-dbs/core/provider/opsmanage"
	controller2 "k8s-dbs/metadata/api/controller"
	dbaccess2 "k8s-dbs/metadata/dbaccess"
	provider2 "k8s-dbs/metadata/provider"
	"log"

	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

const basePath = "/v1"

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

	buildMetaRouter(db, router)

	return &Router{Engine: router}
}

// buildMetaRouter 元数据路由构建
func buildMetaRouter(db *gorm.DB, router *gin.Engine) {
	metaRouter := router.Group(basePath + "/metadata")
	{
		buildAddonMetaRouter(db, metaRouter)

		buildCdMetaRouter(db, metaRouter)

		buildCmpdMetaRouter(db, metaRouter)

		buildCmpvMetaRouter(db, metaRouter)

		buildClusterMetaRouter(db, metaRouter)

		buildOpsMetaRouter(db, metaRouter)

		buildComponentMetaRouter(db, metaRouter)

		buildClusterConfigMetaRouter(db, metaRouter)
	}
}

// buildClusterConfigMetaRouter clusterConfigMeta 管理路由构建
func buildClusterConfigMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	k8sClusterConfigDbAccess := dbaccess2.NewK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := provider2.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	k8sClusterConfigController := controller2.NewK8sClusterConfigController(k8sClusterConfigProvider)
	k8sClusterConfigMetaGroup := metaRouter.Group("/k8s_cluster_config")
	{
		k8sClusterConfigMetaGroup.GET("/id/:id", k8sClusterConfigController.GetK8sClusterConfigByID)
		k8sClusterConfigMetaGroup.GET("/name/:cluster_name", k8sClusterConfigController.GetK8sClusterConfigByName)
		k8sClusterConfigMetaGroup.DELETE("/:id", k8sClusterConfigController.DeleteK8sClusterConfig)
		k8sClusterConfigMetaGroup.POST("", k8sClusterConfigController.CreateK8sClusterConfig)
		k8sClusterConfigMetaGroup.PUT("/:id", k8sClusterConfigController.UpdateK8sClusterConfig)
	}
}

// buildComponentMetaRouter componentMeta 管理路由构建
func buildComponentMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	componentMetaDbAccess := dbaccess2.NewK8sCrdComponentAccess(db)
	componentMetaProvider := provider2.NewK8sCrdComponentProvider(componentMetaDbAccess)
	componentMetaController := controller2.NewComponentController(componentMetaProvider)
	componentMetaGroup := metaRouter.Group("/component")
	{
		componentMetaGroup.GET("/:id", componentMetaController.GetComponent)
	}
}

// buildOpsMetaRouter opsRequestMeta 管理路由构建
func buildOpsMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	opsMetaDbAccess := dbaccess2.NewK8sCrdOpsRequestDbAccess(db)
	opsMetaProvider := provider2.NewK8sCrdOpsRequestProvider(opsMetaDbAccess)
	opsMetaController := controller2.NewOpsController(opsMetaProvider)
	opsMetaGroup := metaRouter.Group("/ops")
	{
		opsMetaGroup.GET("/:id", opsMetaController.GetOps)
	}
}

// buildClusterMetaRouter clusterMeta 管理路由构建
func buildClusterMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	clusterMetaDbAccess := dbaccess2.NewCrdClusterDbAccess(db)
	clusterMetaProvider := provider2.NewK8sCrdClusterProvider(clusterMetaDbAccess)
	clusterMetaController := controller2.NewClusterController(clusterMetaProvider)
	clusterMetaGroup := metaRouter.Group("/cluster")
	{
		clusterMetaGroup.GET("/:id", clusterMetaController.GetCluster)
	}
}

// buildCmpvMetaRouter cmpv 管理路由构建
func buildCmpvMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	cmpvMetaDbAccess := dbaccess2.NewK8sCrdCmpvDbAccess(db)
	cmpvMetaProvider := provider2.NewK8sCrdCmpvProvider(cmpvMetaDbAccess)
	cmpvMetaController := controller2.NewCmpvController(cmpvMetaProvider)
	cmpvMetaGroup := metaRouter.Group("/cmpv")
	{
		cmpvMetaGroup.GET("/:id", cmpvMetaController.GetCmpv)
		cmpvMetaGroup.DELETE("/:id", cmpvMetaController.DeleteCmpv)
		cmpvMetaGroup.POST("", cmpvMetaController.CreateCmpv)
		cmpvMetaGroup.PUT("/:id", cmpvMetaController.UpdateCmpv)
	}
}

// buildCmpdMetaRouter cmpd 管理路由构建
func buildCmpdMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	cmpdMetaDbAccess := dbaccess2.NewK8sCrdCmpdDbAccess(db)
	cmpdMetaProvider := provider2.NewK8sCrdCmpdProvider(cmpdMetaDbAccess)
	cmpdMetaController := controller2.NewCmpdController(cmpdMetaProvider)
	cmpdMetaGroup := metaRouter.Group("/cmpd")
	{
		cmpdMetaGroup.GET("/:id", cmpdMetaController.GetCmpd)
		cmpdMetaGroup.DELETE("/:id", cmpdMetaController.DeleteCmpd)
		cmpdMetaGroup.POST("", cmpdMetaController.CreateCmpd)
		cmpdMetaGroup.PUT("/:id", cmpdMetaController.UpdateCmpd)
	}
}

// buildCdMetaRouter cd 管理路由构建
func buildCdMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	cdMetaDbAccess := dbaccess2.NewK8sCrdClusterDefinitionDbAccess(db)
	cdMetaProvider := provider2.NewK8sCrdClusterDefinitionProvider(cdMetaDbAccess)
	cdMetaController := controller2.NewCdController(cdMetaProvider)
	cdMetaGroup := metaRouter.Group("/cd")
	{
		cdMetaGroup.GET("/:id", cdMetaController.GetCd)
		cdMetaGroup.DELETE("/:id", cdMetaController.DeleteCd)
		cdMetaGroup.POST("", cdMetaController.CreateCd)
		cdMetaGroup.PUT("/:id", cdMetaController.UpdateCd)
	}
}

// buildAddonMetaRouter addon 管理路由构建
func buildAddonMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	addonMetaDbAccess := dbaccess2.NewK8sCrdStorageAddonDbAccess(db)
	addonMetaProvider := provider2.NewK8sCrdStorageAddonProvider(addonMetaDbAccess)
	addonMetaController := controller2.NewAddonController(addonMetaProvider)
	addonMetaGroup := metaRouter.Group("/addon")
	{
		addonMetaGroup.GET("/:id", addonMetaController.GetAddon)
		addonMetaGroup.DELETE("/:id", addonMetaController.DeleteAddon)
		addonMetaGroup.POST("", addonMetaController.CreateAddon)
		addonMetaGroup.PUT("/:id", addonMetaController.UpdateAddon)
	}
}

// buildClusterRouter cluster 管理路由构建
func buildClusterRouter(db *gorm.DB, router *gin.Engine) {
	clusterController := initClusterController(db)
	clusterGroup := router.Group(basePath + "/cluster")
	{

		clusterGroup.POST("/create", clusterController.CreateCluster)
		clusterGroup.POST("/delete", clusterController.DeleteCluster)
		clusterGroup.POST("/describe", clusterController.DescribeCluster)
		clusterGroup.POST("/status", clusterController.GetClusterStatus)

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
func buildService(db *gorm.DB) (*clustermanage.ClusterProvider, *opsmanage.OpsRequestProvider) {
	clusterDbAccess := dbaccess2.NewCrdClusterDbAccess(db)
	clusterDefinitionDbAccess := dbaccess2.NewK8sCrdClusterDefinitionDbAccess(db)
	componentDbAccess := dbaccess2.NewK8sCrdComponentAccess(db)
	componentDefinitionDbAccess := dbaccess2.NewK8sCrdCmpdDbAccess(db)
	componentVersionDbAccess := dbaccess2.NewK8sCrdCmpvDbAccess(db)
	opsReqDbAccess := dbaccess2.NewK8sCrdOpsRequestDbAccess(db)
	k8sClusterConfigDbAccess := dbaccess2.NewK8sClusterConfigDbAccess(db)

	clusterProvider := provider2.NewK8sCrdClusterProvider(clusterDbAccess)
	clusterDefinitionProvider := provider2.NewK8sCrdClusterDefinitionProvider(clusterDefinitionDbAccess)
	componentProvider := provider2.NewK8sCrdComponentProvider(componentDbAccess)
	componentDefinitionProvider := provider2.NewK8sCrdCmpdProvider(componentDefinitionDbAccess)
	componentVersionProvider := provider2.NewK8sCrdCmpvProvider(componentVersionDbAccess)
	opsReqProvider := provider2.NewK8sCrdOpsRequestProvider(opsReqDbAccess)
	k8sClusterConfigProvider := provider2.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)

	clusterService := clustermanage.NewClusterService(
		clusterProvider,
		componentProvider,
		clusterDefinitionProvider,
		componentDefinitionProvider,
		componentVersionProvider,
		k8sClusterConfigProvider,
	)
	opsReqService := opsmanage.NewOpsRequestService(opsReqProvider, clusterProvider, clusterService,
		k8sClusterConfigProvider)
	return clusterService, opsReqService
}

// initClusterController 初始化 ClusterController
func initClusterController(db *gorm.DB) *controller.ClusterController {
	return controller.NewClusterController(buildService(db))
}
