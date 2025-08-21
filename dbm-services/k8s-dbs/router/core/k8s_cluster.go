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
	"k8s-dbs/core/provider"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	routerutil "k8s-dbs/router/util"
	"log/slog"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// BuildK8sClusterRouter k8s集群管理路由构建
func BuildK8sClusterRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	k8sClusterController := initK8sClusterController(db)
	k8sClusterGroup := baseRouter.Group("/k8s_cluster")
	{
		namespaceGroup := k8sClusterGroup.Group("/namespace")
		namespaceGroup.POST("", k8sClusterController.CreateNamespace)
	}
	{
		podGroup := k8sClusterGroup.Group("/pod")
		podGroup.GET("/logs", k8sClusterController.ListPodLogs)
		podGroup.GET("/rawlogs", k8sClusterController.GetPodRawLogs)
		podGroup.GET("", k8sClusterController.GetPodDetail)
		podGroup.POST("/delete", k8sClusterController.DeletePod)
	}
}

// initK8sClusterController 初始化 K8sClusterController
func initK8sClusterController(db *gorm.DB) *controller.K8sController {
	requestRecordDbAccess := metadbaccess.NewClusterRequestRecordDbAccess(db)
	requestRecordProvider := metaprovider.NewClusterRequestRecordProvider(requestRecordDbAccess)

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
		clusterProviderBuilder.WithAddonTopologyDbAccess(clusterTopologyDbAccess))
	if err != nil {
		slog.Warn("failed to create k8s cluster meta provider", "error", err)
		panic(err)
	}

	k8cClusterProvider := provider.NewK8sProvider(requestRecordProvider,
		k8sClusterConfigProvider, clusterMetaProvider)

	return controller.NewK8sController(k8cClusterProvider)
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildK8sClusterRouter)
}
