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

// BuildAddonSpecPlanMetaRouter addon 套餐配置元数据管理路由构建
func BuildAddonSpecPlanMetaRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	metaRouter := baseRouter.Group(BasePath)
	addonSpecPlanMetaController := buildAddonSpecPlanController(db)
	addonSpecPlanMetaGroup := metaRouter.Group("/addon_spec_plan")
	{
		addonSpecPlanMetaGroup.GET("", addonSpecPlanMetaController.GetAddonSpecPlan)
		addonSpecPlanMetaGroup.DELETE("/:id", addonSpecPlanMetaController.DeleteAddonSpecPlan)
		addonSpecPlanMetaGroup.POST("", addonSpecPlanMetaController.CreateAddonSpecPlan)
		addonSpecPlanMetaGroup.PUT("/:id", addonSpecPlanMetaController.UpdateAddonSpecPlan)
	}
}

// buildAddonController 构建 Addon Controller
func buildAddonSpecPlanController(db *gorm.DB) *metacontroller.AddonSpecPlanController {
	addonSpecPlanMetaDbAccess := metadbaccess.GetAddonSpecPlanDbAccess(db)
	storageAddonDbAccess := metadbaccess.GetStorageAddonDbAccess(db)
	componentSpecPlanDbAccess := metadbaccess.GetComponentSpecPlanDbAccess(db)

	specPlanProviderBuilder := metaprovider.AddonSpecPlanProviderBuilder{}
	addonSpecPlanMetaProvider := metaprovider.GetAddonSpecPlanProvider(
		specPlanProviderBuilder.WithSpecPlanDbAccess(addonSpecPlanMetaDbAccess),
		specPlanProviderBuilder.WithStorageAddonDbAccess(storageAddonDbAccess),
		specPlanProviderBuilder.WithComponentSpecPlanDbAccess(componentSpecPlanDbAccess),
	)

	addonSpecPlanMetaController := metacontroller.NewAddonSpecPlanController(addonSpecPlanMetaProvider)
	return addonSpecPlanMetaController
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildAddonSpecPlanMetaRouter)
}
