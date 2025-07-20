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

package helper

import (
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	"gorm.io/gorm"
)

// BuildClusterMetaProvider 构建 K8sCrdClusterProviderImpl
func BuildClusterMetaProvider(db *gorm.DB) *metaprovider.K8sCrdClusterProviderImpl {
	clusterMetaDbAccess := metadbaccess.NewCrdClusterDbAccess(db)
	addonMetaDbAccess := metadbaccess.NewK8sCrdStorageAddonDbAccess(db)
	clusterTagDbAccess := metadbaccess.NewK8sCrdClusterTagDbAccess(db)
	k8sClusterConfigDbAccess := metadbaccess.NewK8sClusterConfigDbAccess(db)
	clusterTopologyDbAccess := metadbaccess.NewAddonTopologyDbAccess(db)

	clusterMetaProviderBuilder := metaprovider.K8sCrdClusterProviderBuilder{}
	clusterMetaProvider, err := metaprovider.NewK8sCrdClusterProvider(
		clusterMetaProviderBuilder.WithClusterDbAccess(clusterMetaDbAccess),
		clusterMetaProviderBuilder.WithAddonDbAccess(addonMetaDbAccess),
		clusterMetaProviderBuilder.WithK8sClusterConfigDbAccess(k8sClusterConfigDbAccess),
		clusterMetaProviderBuilder.WithClusterTagDbAccess(clusterTagDbAccess),
		clusterMetaProviderBuilder.WithAddonTopologyDbAccess(clusterTopologyDbAccess),
	)
	if err != nil {
		slog.Error("failed to build cluster meta provider", "error", err)
		panic(err)
	}
	return clusterMetaProvider
}
