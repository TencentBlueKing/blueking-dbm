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

package dataweb

import (
	"k8s-dbs/dataweb/api/controller"
	routerutil "k8s-dbs/router/util"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// BuildClusterRouter cluster 管理路由构建
func BuildClusterRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	dataWebRouter := baseRouter.Group(BasePath)
	clusterGroup := dataWebRouter.Group("/cluster")
	clusterController := initClusterController(db)
	{
		clusterGroup.POST("/create", clusterController.CreateCluster)
	}
}

// initClusterController 初始化 ClusterController
func initClusterController(db *gorm.DB) *controller.ClusterController {
	clusterProvider := routerutil.BuildClusterProvider(db)
	return controller.NewClusterController(clusterProvider)
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildClusterRouter)
}
