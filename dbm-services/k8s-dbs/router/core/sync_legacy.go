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
	"k8s-dbs/infrastructure/thirdapi"
	routerutil "k8s-dbs/router/util"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// BuildSyncLegacyRouter 存量集群同步路由构建
func BuildSyncLegacyRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	syncLegacyController := initSyncLegacyController(db)
	clusterGroup := baseRouter.Group("/cluster")
	{
		clusterGroup.POST("/sync_all_to_dbm", syncLegacyController.SyncLegacyClusters)
		clusterGroup.POST("/sync_to_dbm_by_filter", syncLegacyController.SyncFilteredClusters)
	}
}

// initSyncLegacyController 初始化 SyncLegacyController
func initSyncLegacyController(db *gorm.DB) *controller.SyncLegacyController {
	clusterMetaProvider := routerutil.BuildClusterMetaProvider(db)
	configProvider := routerutil.BuildK8sClusterConfigProvider(db)
	dbmAPIService := thirdapi.NewDbmAPIService()
	syncLegacyProvider := coreprovider.NewSyncLegacyProvider(
		clusterMetaProvider, configProvider, dbmAPIService)
	return controller.NewSyncLegacyController(syncLegacyProvider)
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildSyncLegacyRouter)
}
