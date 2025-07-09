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
	metacontroller "k8s-dbs/metadata/api/controller"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// buildMetaRouter 元数据路由构建
func buildMetaRouter(db *gorm.DB, router *gin.Engine) {
	metaRouter := router.Group(basePath + "/metadata")
	{
		buildAddonMetaRouter(db, metaRouter)

		buildClusterMetaRouter(db, metaRouter)

		buildOpsMetaRouter(db, metaRouter)

		buildComponentMetaRouter(db, metaRouter)

		buildClusterConfigMetaRouter(db, metaRouter)

		buildOperationMetaRouter(db, metaRouter)

		buildClusterOpMetaRouter(db, metaRouter)

		buildComponentOpMetaRouter(db, metaRouter)

		buildClusterHelmRepoMetaRouter(db, metaRouter)

		buildAddonHelmRepoMetaRouter(db, metaRouter)

		buildClusterReleaseMetaRouter(db, metaRouter)

		buildK8sClusterAddonsRouter(db, metaRouter)

		buildAddonClusterVersionRouter(db, metaRouter)

		buildRequestRecordRouter(db, metaRouter)
	}
}

// buildClusterConfigMetaRouter clusterConfigMeta 管理路由构建
func buildClusterConfigMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	k8sClusterConfigController := metacontroller.NewK8sClusterConfigController(k8sClusterConfigProvider)
	k8sClusterConfigMetaGroup := metaRouter.Group("/k8s_cluster_config")
	{
		k8sClusterConfigMetaGroup.GET("/id/:id", k8sClusterConfigController.GetK8sClusterConfigByID)
		k8sClusterConfigMetaGroup.GET("/name/:cluster_name", k8sClusterConfigController.GetK8sClusterConfigByName)
		k8sClusterConfigMetaGroup.DELETE("/:id", k8sClusterConfigController.DeleteK8sClusterConfig)
		k8sClusterConfigMetaGroup.POST("", k8sClusterConfigController.CreateK8sClusterConfig)
		k8sClusterConfigMetaGroup.PUT("/:id", k8sClusterConfigController.UpdateK8sClusterConfig)
	}
}

// buildClusterReleaseMetaRouter clusterReleaseMeta 管理路由构建
func buildClusterReleaseMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	addonClusterReleaseDbAccess := metadbaccess.NewAddonClusterReleaseDbAccess(db)
	addonClusterReleaseProvider := metaprovider.NewAddonClusterReleaseProvider(addonClusterReleaseDbAccess)
	clusterReleaseController := metacontroller.NewClusterReleaseController(addonClusterReleaseProvider)
	k8sClusterConfigMetaGroup := metaRouter.Group("/cluster_release")
	{
		k8sClusterConfigMetaGroup.GET("/id/:id", clusterReleaseController.GetClusterRelease)
		k8sClusterConfigMetaGroup.GET("/name/:release_name/namespace/:namespace",
			clusterReleaseController.GetClusterReleaseByParam)
	}
}

// buildComponentMetaRouter componentMeta 管理路由构建
func buildComponentMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	componentMetaDbAccess := metadbaccess.NewK8sCrdComponentAccess(db)
	componentMetaProvider := metaprovider.NewK8sCrdComponentProvider(componentMetaDbAccess)
	componentMetaController := metacontroller.NewComponentController(componentMetaProvider)
	componentMetaGroup := metaRouter.Group("/component")
	{
		componentMetaGroup.GET("/:id", componentMetaController.GetComponent)
	}
}

// buildOpsMetaRouter opsRequestMeta 管理路由构建
func buildOpsMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	opsMetaDbAccess := metadbaccess.NewK8sCrdOpsRequestDbAccess(db)
	opsMetaProvider := metaprovider.NewK8sCrdOpsRequestProvider(opsMetaDbAccess)
	opsMetaController := metacontroller.NewOpsController(opsMetaProvider)
	opsMetaGroup := metaRouter.Group("/ops")
	{
		opsMetaGroup.GET("/:id", opsMetaController.GetOps)
	}
}

// buildClusterMetaRouter clusterMeta 管理路由构建
func buildClusterMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	clusterMetaDbAccess := metadbaccess.NewCrdClusterDbAccess(db)
	addonMetaDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := metadbaccess.NewK8sCrdClusterTagDbAccess(db)
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	clusterMetaProvider := metaprovider.NewK8sCrdClusterProvider(clusterMetaDbAccess,
		addonMetaDbAccess, clusterTagDbAccess, k8sClusterConfigDbAccess)
	clusterMetaController := metacontroller.NewClusterController(clusterMetaProvider)
	clusterMetaGroup := metaRouter.Group("/cluster")
	{
		clusterMetaGroup.GET("/:id", clusterMetaController.GetCluster)
		clusterMetaGroup.GET("/search", clusterMetaController.ListCluster)
	}
}

// buildAddonMetaRouter addon 元数据管理路由构建
func buildAddonMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	addonMetaDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)
	addonMetaProvider := metaprovider.NewK8sCrdStorageAddonProvider(addonMetaDbAccess)
	addonMetaController := metacontroller.NewAddonController(addonMetaProvider)
	addonMetaGroup := metaRouter.Group("/addon")
	{
		addonMetaGroup.GET("", addonMetaController.ListAddons)
		addonMetaGroup.GET("/:id", addonMetaController.GetAddon)
		addonMetaGroup.DELETE("/:id", addonMetaController.DeleteAddon)
		addonMetaGroup.POST("", addonMetaController.CreateAddon)
		addonMetaGroup.PUT("/:id", addonMetaController.UpdateAddon)
	}
}

// buildOperationMetaRouter operation definition 管理路由构建
func buildOperationMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	metaDbAccess := metadbaccess.NewOperationDefinitionDbAccess(db)
	metaProvider := metaprovider.NewOperationDefinitionProvider(metaDbAccess)
	metaController := metacontroller.NewOperationDefinitionController(metaProvider)
	addonMetaGroup := metaRouter.Group("/operation_definition")
	{
		addonMetaGroup.GET("", metaController.ListOperationDefinitions)
		addonMetaGroup.POST("", metaController.CreateOperationDefinition)
	}
}

// buildClusterOpMetaRouter cluster operation 管理路由构建
func buildClusterOpMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	clusterOpDbAccess := metadbaccess.NewClusterOperationDbAccess(db)
	opDefDbAccess := metadbaccess.NewOperationDefinitionDbAccess(db)
	metaProvider := metaprovider.NewClusterOperationProvider(clusterOpDbAccess, opDefDbAccess)
	metaController := metacontroller.NewClusterOperationController(metaProvider)
	addonMetaGroup := metaRouter.Group("/cluster_operation")
	{
		addonMetaGroup.GET("", metaController.ListClusterOperations)
		addonMetaGroup.POST("", metaController.CreateClusterOperation)
	}
}

// buildComponentOpMetaRouter component operation 管理路由构建
func buildComponentOpMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	componentOpDbAccess := metadbaccess.NewComponentOperationDbAccess(db)
	opDefDbAccess := metadbaccess.NewOperationDefinitionDbAccess(db)
	metaProvider := metaprovider.NewComponentOperationProvider(componentOpDbAccess, opDefDbAccess)
	metaController := metacontroller.NewComponentOperationController(metaProvider)
	addonMetaGroup := metaRouter.Group("/component_operation")
	{
		addonMetaGroup.GET("", metaController.ListComponentOperations)
		addonMetaGroup.POST("", metaController.CreateComponentOperation)
	}
}

// buildClusterHelmRepoMetaRouter Helm repository 管理路由构建
func buildClusterHelmRepoMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	dbAccess := metadbaccess.NewAddonClusterHelmRepoDbAccess(db)
	metaProvider := metaprovider.NewAddonClusterHelmRepoProvider(dbAccess)
	metaController := metacontroller.NewClusterHelmRepoController(metaProvider)
	repoMetaGroup := metaRouter.Group("/addoncluster_helm_repo")
	{
		repoMetaGroup.GET("", metaController.GetClusterHelmRepoByID)
		repoMetaGroup.POST("", metaController.CreateClusterHelmRepo)
	}
}

// buildAddonHelmRepoMetaRouter addon Helm repository 管理路由构建
func buildAddonHelmRepoMetaRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	dbAccess := metadbaccess.NewAddonHelmRepoDbAccess(db)
	metaProvider := metaprovider.NewAddonHelmRepoProvider(dbAccess)
	metaController := metacontroller.NewAddonHelmRepoController(metaProvider)
	repoMetaGroup := metaRouter.Group("/addon_helm_repo")
	{
		repoMetaGroup.GET("", metaController.GetAddonHelmRepoByID)
		repoMetaGroup.POST("", metaController.CreateAddonHelmRepo)
	}
}

// buildK8sClusterAddonsRouter cluster addons 管理路由构建
func buildK8sClusterAddonsRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	kcaDbAccess := metadbaccess.NewK8sClusterAddonsDbAccess(db)
	saDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)

	metaProvider := metaprovider.NewK8sClusterAddonsProvider(kcaDbAccess, saDbAccess)
	metaController := metacontroller.NewK8sClusterAddonsController(metaProvider)
	repoMetaGroup := metaRouter.Group("/k8s_cluster_addons")
	{
		repoMetaGroup.GET("/:id", metaController.GetAddon)
		repoMetaGroup.GET("", metaController.GetAddonsByClusterName)
	}
}

// buildAddonClusterVersionRouter addon cluster version 管理路由构建
func buildAddonClusterVersionRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	metaDbAccess := metadbaccess.NewAddonClusterVersionDbAccess(db)

	metaProvider := metaprovider.NewAddonClusterVersionProvider(metaDbAccess)
	metaController := metacontroller.NewAddonClusterVersionController(metaProvider)
	metaGroup := metaRouter.Group("/addoncluster_version")
	{
		metaGroup.GET("", metaController.ListAcVersions)
		metaGroup.GET("/:id", metaController.GetAcVersion)
		metaGroup.DELETE("/:id", metaController.DeleteAcVersion)
		metaGroup.POST("", metaController.CreateAcVersion)
		metaGroup.PUT("/:id", metaController.UpdateAcVersion)
	}
}

// buildRequestRecordRouter cluster request record 管理路由构建
func buildRequestRecordRouter(db *gorm.DB, metaRouter *gin.RouterGroup) {
	metaDbAccess := metadbaccess.NewClusterRequestRecordDbAccess(db)
	metaProvider := metaprovider.NewClusterRequestRecordProvider(metaDbAccess)
	metaController := metacontroller.NewClusterRequestRecordController(metaProvider)

	metaGroup := metaRouter.Group("/cluster_request_record")
	{
		metaGroup.POST("/search", metaController.ListClusterRecords)
	}
}
