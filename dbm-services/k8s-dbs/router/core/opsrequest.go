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
	routerutil "k8s-dbs/router/util"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// BuildOpsRequestRouter opsRequest 运维操作路由构建
func BuildOpsRequestRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	opsController := initOpsController(db)
	opsRequestGroup := baseRouter.Group("/opsRequest")
	{
		opsRequestGroup.POST("/vscaling", opsController.VerticalScaling)
		opsRequestGroup.POST("/hscaling", opsController.HorizontalScaling)
		opsRequestGroup.POST("/start", opsController.StartCluster)
		opsRequestGroup.POST("/stop", opsController.StopCluster)
		opsRequestGroup.POST("/restart", opsController.RestartCluster)
		opsRequestGroup.POST("/upgrade", opsController.UpgradeCluster)
		opsRequestGroup.POST("/vexpansion", opsController.VolumeExpansion)
		opsRequestGroup.POST("/expose", opsController.ExposeCluster)
		opsRequestGroup.POST("/describe", opsController.DescribeOpsRequest)
		opsRequestGroup.POST("/status", opsController.GetOpsRequestStatus)
	}
}

// initOpsController 初始化 OpsController
func initOpsController(db *gorm.DB) *controller.OpsController {
	clusterProvider := routerutil.BuildClusterProvider(db)
	opsRequestProvider := routerutil.BuildOpsRequestProvider(db)
	clusterMetaProvider := routerutil.BuildClusterMetaProvider(db)
	componentProvider := routerutil.BuildComponentProvider(db)
	return controller.NewOpsController(
		clusterProvider,
		clusterMetaProvider,
		componentProvider,
		opsRequestProvider,
	)
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildOpsRequestRouter)
}
