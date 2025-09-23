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

package informers

import (
	"context"
	"fmt"
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

// StartInformers 启动 informer
func StartInformers(ctx context.Context) {
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
		clusterInformer := NewClusterInformer(clusterConfig, clusterMetaProvider)
		startGenericInformer(ctx, clusterConfig, clusterInformer, "clusterInformer")

		opsInformer := NewOpsRequestInformer(clusterConfig, clusterMetaProvider, opsMetaProvider)
		startGenericInformer(ctx, clusterConfig, opsInformer, "opsInformer")
	}
	slog.Info("Finished starting all opsInformer")
}

// DbsInformerStarter 定义所有 informer 必须实现的启动方法
type DbsInformerStarter interface {
	Start(ctx context.Context, factory dynamicinformer.DynamicSharedInformerFactory) error
}

// startGenericInformer 封装公共的 informer 启动逻辑
func startGenericInformer(
	ctx context.Context,
	clusterConfig *entitys.K8sClusterConfigEntity,
	informerStarter DbsInformerStarter,
	informerName string,
) {
	slog.Info(fmt.Sprintf("Begin to starting %s", informerName),
		"k8sClusterName", clusterConfig.ClusterName)

	k8sClient, err := commutil.NewK8sClient(clusterConfig)
	if err != nil {
		slog.Error("failed to create k8s client", "error", err)
		return
	}

	factory := dynamicinformer.NewDynamicSharedInformerFactory(k8sClient.DynamicClient, time.Second*30)
	informerCtx, cancelInformer := context.WithCancel(ctx)

	// 调用具体 informer 的 Start 方法
	go func() {
		if err := informerStarter.Start(informerCtx, factory); err != nil {
			cancelInformer()
			slog.Error(fmt.Sprintf("%s failed to start", informerName), "error", err)
			return
		}
	}()

	// 监听 ctx.Done() 取消 informer
	go func() {
		<-ctx.Done()
		cancelInformer()
	}()

	slog.Info(fmt.Sprintf("Finished starting %s", informerName),
		"k8sClusterName", clusterConfig.ClusterName)
}
