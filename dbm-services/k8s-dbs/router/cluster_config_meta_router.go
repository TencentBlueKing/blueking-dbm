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

// BuildClusterConfigMetaRouter clusterConfigMeta 管理路由构建
func BuildClusterConfigMetaRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	metaRouter := baseRouter.Group("/metadata")
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	k8sClusterConfigController := metacontroller.NewK8sClusterConfigController(k8sClusterConfigProvider)
	k8sClusterConfigMetaGroup := metaRouter.Group("/k8s_cluster_config")
	{
		k8sClusterConfigMetaGroup.DELETE("/:id", k8sClusterConfigController.DeleteK8sClusterConfig)
		k8sClusterConfigMetaGroup.POST("", k8sClusterConfigController.CreateK8sClusterConfig)
		k8sClusterConfigMetaGroup.PUT("/:id", k8sClusterConfigController.UpdateK8sClusterConfig)
		k8sClusterConfigMetaGroup.GET("/regions", k8sClusterConfigController.GetRegionsByVisibility)
	}
}

func init() {
	RegisterAPIRouterBuilder(BuildClusterConfigMetaRouter)
}
