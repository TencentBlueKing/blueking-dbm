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

package informer

import (
	"context"
	commconst "k8s-dbs/common/constant"
	commutil "k8s-dbs/common/util"
	entitys "k8s-dbs/metadata/entity"

	"k8s-dbs/core/util"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"

	routerutil "k8s-dbs/router/util"

	"log/slog"
	"time"

	"k8s.io/client-go/dynamic/dynamicinformer"
)

// StartInformer 启动 informer
func StartInformer(ctx context.Context) {
	k8sClusterConfigProvider := metaprovider.
		NewK8sClusterConfigProvider(metadbaccess.NewK8sClusterConfigDbAccess(util.Db.GormDb))
	opsMetaProvider := metaprovider.
		NewK8sCrdOpsRequestProvider(metadbaccess.NewK8sCrdOpsRequestDbAccess(util.Db.GormDb))
	clusterMetaProvider := routerutil.BuildClusterMetaProvider(util.Db.GormDb)

	k8sClusterConfigs, err := k8sClusterConfigProvider.ListConfigsByLimit(commconst.MaxFetchSize)
	if err != nil || len(k8sClusterConfigs) == 0 {
		slog.Error("failed to find k8s cluster config", "error", err)
		return
	}

	for _, clusterConfig := range k8sClusterConfigs {
		startOpsInformer(ctx, clusterConfig, clusterMetaProvider, opsMetaProvider)
	}
	slog.Info("Finished starting all opsInformer")
}

// startOpsInformer 启动单个 opsInformer
func startOpsInformer(
	ctx context.Context,
	clusterConfig *entitys.K8sClusterConfigEntity,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	opsMetaProvider metaprovider.K8sCrdOpsRequestProvider,
) {
	slog.Info("Begin to starting opsInformer", "k8sClusterName", clusterConfig.ClusterName)
	k8sClient, err := commutil.NewK8sClient(clusterConfig)
	if err != nil {
		slog.Error("failed to create k8s client", "error", err)
		return
	}

	factory := dynamicinformer.NewDynamicSharedInformerFactory(
		k8sClient.DynamicClient,
		time.Second*30,
	)
	ctxInformer, cancelInformer := context.WithCancel(ctx)
	opsInformer := NewOpsRequestInformer(clusterConfig, clusterMetaProvider, opsMetaProvider)

	go func() {
		if err = opsInformer.Start(ctxInformer, factory); err != nil {
			cancelInformer()
			slog.Error("failed to start ops informer", "error", err)
			return
		}
	}()

	go func() {
		<-ctx.Done()
		cancelInformer()
	}()
	slog.Info("Finished starting opsInformer", "k8sClusterName", clusterConfig.ClusterName)
}
