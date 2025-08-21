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

// BuildAddonRouter 存储插件管理路由构建
func BuildAddonRouter(db *gorm.DB, baseRouter *gin.RouterGroup) {
	addonController := initAddonController(db)
	addonGroup := baseRouter.Group("/addon")
	{
		addonGroup.POST("/install", addonController.InstallAddon)
		addonGroup.POST("/uninstall", addonController.UninstallAddon)
		addonGroup.POST("/upgrade", addonController.UpgradeAddon)
	}
}

// initAddonController 初始化 AddonController
func initAddonController(db *gorm.DB) *controller.AddonController {
	requestRecordDbAccess := metadbaccess.NewClusterRequestRecordDbAccess(db)
	requestRecordProvider := metaprovider.NewClusterRequestRecordProvider(requestRecordDbAccess)

	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	k8sClusterConfigProvider := metaprovider.NewK8sClusterConfigProvider(k8sClusterConfigDbAccess)

	addonHelmRepoDbAccess := metadbaccess.NewAddonHelmRepoDbAccess(db)
	addonHelmRepoProvider := metaprovider.NewAddonHelmRepoProvider(addonHelmRepoDbAccess)

	addonMetaDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)
	addonMetaProvider := metaprovider.NewK8sCrdStorageAddonProvider(addonMetaDbAccess)

	clusterAddonsMetaDbAccess := metadbaccess.NewK8sClusterAddonsDbAccess(db)
	clusterAddonsMetaProvider := metaprovider.NewK8sClusterAddonsProvider(clusterAddonsMetaDbAccess, addonMetaDbAccess)

	addonProviderBuilder := &provider.AddonProviderBuilder{}
	addonProvider, err := provider.NewAddonProvider(
		addonProviderBuilder.WithReqRecordMeta(requestRecordProvider),
		addonProviderBuilder.WithAddonMeta(addonMetaProvider),
		addonProviderBuilder.WithClusterAddonMeta(clusterAddonsMetaProvider),
		addonProviderBuilder.WithClusterConfigMeta(k8sClusterConfigProvider),
		addonProviderBuilder.WithAddonHelmRepoMeta(addonHelmRepoProvider),
	)
	if err != nil {
		slog.Error("failed to build addon provider", "error", err)
		panic(err)
	}
	return controller.NewAddonController(addonProvider)
}

func init() {
	routerutil.RegisterAPIRouterBuilder(BuildAddonRouter)
}
