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
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	routerutil "k8s-dbs/router/util"
	"log/slog"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// BuildComponentRouter component 管理路由构建
func BuildComponentRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	componentController := initComponentController(db)
	componentGroup := baseRouter.Group("/component")
	{
		componentGroup.POST("/describe", componentController.DescribeComponent)
		componentGroup.GET("/services", componentController.GetComponentService)
		componentGroup.GET("/pods", componentController.ListPods)
	}
}

// initComponentController 初始化 ComponentController
func initComponentController(db *gorm.DB) *controller.ComponentController {
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)

	clusterMetaDbAccess := metadbaccess.NewCrdClusterDbAccess(db)
	addonMetaDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := metadbaccess.NewK8sCrdClusterTagDbAccess(db)
	clusterTopologyDbAccess := metadbaccess.NewAddonTopologyDbAccess(db)
	clusterProviderBuilder := metaprovider.K8sCrdClusterProviderBuilder{}
	clusterMetaProvider, err := metaprovider.NewK8sCrdClusterProvider(
		clusterProviderBuilder.WithClusterDbAccess(clusterMetaDbAccess),
		clusterProviderBuilder.WithAddonDbAccess(addonMetaDbAccess),
		clusterProviderBuilder.WithK8sClusterConfigDbAccess(k8sClusterConfigDbAccess),
		clusterProviderBuilder.WithClusterTagDbAccess(clusterTagDbAccess),
		clusterProviderBuilder.WithAddonTopologyDbAccess(clusterTopologyDbAccess),
	)
	if err != nil {
		slog.Error("failed to create cluster meta provider", "clusterProvider", clusterProviderBuilder)
		panic(err)
	}

	componentProvider := coreprovider.NewComponentProvider(k8sClusterConfigProvider, clusterMetaProvider)
	return controller.NewComponentController(componentProvider)
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildComponentRouter)
}
