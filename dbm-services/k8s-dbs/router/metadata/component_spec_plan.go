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

package metadata

import (
	metacontroller "k8s-dbs/metadata/api/controller"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	routerutil "k8s-dbs/router/util"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// BuildComponentSpecPlanMetaRouter component 套餐配置元数据管理路由构建
func BuildComponentSpecPlanMetaRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	metaRouter := baseRouter.Group(BasePath)
	componentSpecPlanMetaController := buildComponentSpecPlanController(db)
	componentSpecPlanMetaGroup := metaRouter.Group("/component_spec_plan")
	{
		componentSpecPlanMetaGroup.GET("", componentSpecPlanMetaController.ListComponentSpecPlans)
		componentSpecPlanMetaGroup.GET("/:id", componentSpecPlanMetaController.GetComponentSpecPlan)
		componentSpecPlanMetaGroup.DELETE("/:id", componentSpecPlanMetaController.DeleteComponentSpecPlan)
		componentSpecPlanMetaGroup.POST("", componentSpecPlanMetaController.CreateComponentSpecPlan)
		componentSpecPlanMetaGroup.PUT("/:id", componentSpecPlanMetaController.UpdateComponentSpecPlan)
	}
}

// buildComponentController 构建 component Controller
func buildComponentSpecPlanController(db *gorm.DB) *metacontroller.ComponentSpecPlanController {
	componentSpecPlanMetaDbAccess := metadbaccess.GetComponentSpecPlanDbAccess(db)
	componentSpecPlanMetaProvider := metaprovider.GetComponentSpecPlanProvider(componentSpecPlanMetaDbAccess)
	componentSpecPlanMetaController := metacontroller.NewComponentSpecPlanController(componentSpecPlanMetaProvider)
	return componentSpecPlanMetaController
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildComponentSpecPlanMetaRouter)
}
