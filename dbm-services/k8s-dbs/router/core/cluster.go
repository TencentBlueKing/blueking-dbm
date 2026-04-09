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
	routerutil "k8s-dbs/router/util"

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
		clusterGroup.POST("/partial_update", clusterController.PartialUpdateCluster)
		clusterGroup.POST("/delete", clusterController.DeleteCluster)
		clusterGroup.POST("/describe", clusterController.DescribeCluster)
		clusterGroup.GET("/services", clusterController.GetClusterService)
		clusterGroup.POST("/status", clusterController.GetClusterStatus)
		clusterGroup.POST("/event", clusterController.GetClusterEvent)
		clusterGroup.POST("/bind-domain", clusterController.BindDomain)
		clusterGroup.POST("/unbind-domain", clusterController.UnbindDomain)

	}
}

// initClusterController 初始化 ClusterController
func initClusterController(db *gorm.DB) *controller.ClusterController {
	clusterProvider := routerutil.BuildClusterProvider(db)
	k8sClusterConfigProvider := routerutil.BuildK8sClusterConfigProvider(db)
	clusterMetaProvider := routerutil.BuildClusterMetaProvider(db)
	componentProvider := coreprovider.NewComponentProvider(k8sClusterConfigProvider, clusterMetaProvider)
	return controller.NewClusterController(
		clusterProvider,
		clusterMetaProvider,
		componentProvider,
	)
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildClusterRouter)
}
