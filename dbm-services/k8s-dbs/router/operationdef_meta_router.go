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

// BuildOperationMetaRouter operation definition 管理路由构建
func BuildOperationMetaRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	metaRouter := baseRouter.Group("/metadata")
	metaDbAccess := metadbaccess.NewOperationDefinitionDbAccess(db)
	metaProvider := metaprovider.NewOperationDefinitionProvider(metaDbAccess)
	metaController := metacontroller.NewOperationDefinitionController(metaProvider)
	addonMetaGroup := metaRouter.Group("/operation_definition")
	{
		addonMetaGroup.GET("", metaController.ListOperationDefinitions)
		addonMetaGroup.POST("", metaController.CreateOperationDefinition)
	}
}

func init() {
	RegisterAPIRouterBuilder(BuildOperationMetaRouter)
}
