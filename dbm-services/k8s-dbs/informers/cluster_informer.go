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
	coreconst "k8s-dbs/core/constant"
	infrautil "k8s-dbs/infrastructure/util"
	"os"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	"k8s.io/client-go/tools/cache"

	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"

	"k8s-dbs/infrastructure/thirdapi"

	appsv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	"k8s.io/client-go/dynamic/dynamicinformer"
)

// ClusterInformer Cluster informer 结构体
type ClusterInformer struct {
	k8sClusterConfig    *metaentity.K8sClusterConfigEntity
	clusterMetaProvider metaprovider.K8sCrdClusterProvider
}

// NewClusterInformer Cluster informer 构造函数
func NewClusterInformer(
	k8sClusterConfig *metaentity.K8sClusterConfigEntity,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
) *ClusterInformer {
	return &ClusterInformer{
		k8sClusterConfig:    k8sClusterConfig,
		clusterMetaProvider: clusterMetaProvider,
	}
}

// Start 启动
func (o *ClusterInformer) Start(
	ctx context.Context,
	factory dynamicinformer.DynamicSharedInformerFactory,
) error {
	slog.Info("Starting ClusterInformer...", "k8sClusterName", o.k8sClusterConfig.ClusterName)
	handler := cache.ResourceEventHandlerFuncs{
		UpdateFunc: o.OnUpdate,
	}
	if err := DoStart(
		ctx,
		kbtypes.ClusterGVR(),
		factory,
		handler,
		"ClusterInformer",
	); err != nil {
		slog.Error("Error starting informer for ClusterInformer. ", "error", err)
		return err
	}
	slog.Info("Shutting down informer...", "k8sClusterName", o.k8sClusterConfig.ClusterName)
	return nil
}

// OnUpdate 处理 opsRequest 更新事件
func (o *ClusterInformer) OnUpdate(_, newObj interface{}) {
	// 1. 类型转换
	newUnstructured, ok := newObj.(*unstructured.Unstructured)
	if !ok {
		slog.Error("failed to cast newObj to Unstructured")
		return
	}

	var cluster appsv1.Cluster
	if err := runtime.DefaultUnstructuredConverter.FromUnstructured(newUnstructured.Object, &cluster); err != nil {
		slog.Error("failed to convert to Cluster", "err", err)
		return
	}

	// 2. 查询集群实体
	entity, err := o.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		ClusterName:        cluster.Name,
		Namespace:          cluster.Namespace,
		K8sClusterConfigID: o.k8sClusterConfig.ID,
	})

	if err != nil || entity == nil {
		slog.Debug("failed to find cluster",
			"clusterEntity", fmt.Sprintf("%+v", entity), "err", err)
		return
	}

	// 3. 检查状态变更
	newPhase := string(cluster.Status.Phase)
	if entity.Status == newPhase {
		return // 状态未变化
	}

	slog.Info("Cluster status changed",
		"cluster", fmt.Sprintf("%s/%s", cluster.Namespace, cluster.Name),
		"old", entity.Status, "new", newPhase)

	// 4. 处理异常状态
	if cluster.Status.Phase == appsv1.AbnormalClusterPhase ||
		cluster.Status.Phase == appsv1.FailedClusterPhase {
		if os.Getenv(coreconst.AsyncToDBMEnv) == coreconst.AsyncToDBMEnabled {
			infrautil.AsyncClusterAbnormal(entity, thirdapi.GetDbmAPIService())
		}
	}

	// 5. 更新状态
	entity.Status = newPhase
	if _, err := o.clusterMetaProvider.UpdateCluster(entity); err != nil {
		slog.Error("failed to update cluster",
			"cluster", cluster.Name, "err", err)
	}
}
