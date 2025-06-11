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
	"k8s-dbs/core/api/controller"
	"k8s-dbs/core/provider"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// buildAddonRouter 存储插件管理路由构建
func buildAddonRouter(db *gorm.DB, router *gin.Engine) {
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

	addonProvider := provider.NewAddonProvider(
		requestRecordProvider,
		k8sClusterConfigProvider,
		addonHelmRepoProvider,
		clusterAddonsMetaProvider,
		addonMetaProvider,
	)

	addonController := controller.NewAddonController(addonProvider)
	addonGroup := router.Group(basePath + "/addon")
	{
		addonGroup.POST("/deploy", addonController.DeployAddon)
	}
}
