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

package terminal

import (
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	routerutil "k8s-dbs/router/util"
	"k8s-dbs/terminal/api/controller"
	terminalprovider "k8s-dbs/terminal/provider"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// BuildTerminalRouter cluster 管理路由构建
func BuildTerminalRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	terminalRouter := baseRouter.Group(BasePath)
	terminalController := initTerminalController(db)
	{
		terminalRouter.GET("", terminalController.OpenTerminal)
	}
}

// initClusterController 初始化 ClusterController
func initTerminalController(db *gorm.DB) *controller.ContainerController {
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)
	containerProvider := terminalprovider.NewTerminalProvider(k8sClusterConfigProvider)
	terminalController := controller.NewContainerController(containerProvider)
	return terminalController
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildTerminalRouter)
}
