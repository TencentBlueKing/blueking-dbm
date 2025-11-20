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

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	"k8s.io/client-go/tools/cache"

	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"

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
	newUnstructured, ok := newObj.(*unstructured.Unstructured)
	if !ok {
		slog.Error("failed to cast newObj to Unstructured")
		return
	}

	var newCluster *appsv1.Cluster
	if err := runtime.
		DefaultUnstructuredConverter.FromUnstructured(newUnstructured.Object, &newCluster); err != nil {
		slog.Error("failed to cast oldUnstructured to Cluster")
		return
	}
	clusterName := newCluster.Name
	nameSpace := newCluster.GetNamespace()
	status := newCluster.Status
	clusterEntity, err := o.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		ClusterName:        clusterName,
		Namespace:          nameSpace,
		K8sClusterConfigID: o.k8sClusterConfig.ID,
	})
	if err != nil || clusterEntity == nil {
		slog.Error("failed to find cluster",
			"clusterEntity", fmt.Sprintf("%+v", clusterEntity), "err", err)
		return
	}
	if clusterEntity.Status != string(status.Phase) {
		slog.Info("Cluster entity status changed",
			"clusterName", clusterName, "oldPhase", clusterEntity.Status, "newPhase", status.Phase)
		clusterEntity.Status = string(status.Phase)
		_, err = o.clusterMetaProvider.UpdateCluster(clusterEntity)
		if err != nil {
			slog.Error("failed to update cluster entity",
				"clusterName", clusterName, "err", err)
			return
		}
	}
}
