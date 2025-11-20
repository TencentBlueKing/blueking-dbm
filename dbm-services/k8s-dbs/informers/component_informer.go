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

// ComponentInformer Component informer 结构体
type ComponentInformer struct {
	k8sClusterConfig      *metaentity.K8sClusterConfigEntity
	clusterMetaProvider   metaprovider.K8sCrdClusterProvider
	componentMetaProvider metaprovider.K8sCrdComponentProvider
}

// NewComponentInformer Component informer 构造函数
func NewComponentInformer(
	k8sClusterConfig *metaentity.K8sClusterConfigEntity,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	componentMetaProvider metaprovider.K8sCrdComponentProvider,
) *ComponentInformer {
	return &ComponentInformer{
		k8sClusterConfig:      k8sClusterConfig,
		clusterMetaProvider:   clusterMetaProvider,
		componentMetaProvider: componentMetaProvider,
	}
}

// Start 启动
func (o *ComponentInformer) Start(
	ctx context.Context,
	factory dynamicinformer.DynamicSharedInformerFactory,
) error {
	slog.Info("Starting ComponentInformer...", "k8sClusterName", o.k8sClusterConfig.ClusterName)
	handler := cache.ResourceEventHandlerFuncs{
		UpdateFunc: o.OnUpdate,
	}
	if err := DoStart(
		ctx,
		kbtypes.ComponentGVR(),
		factory,
		handler,
		"ComponentInformer",
	); err != nil {
		slog.Error("Error starting informer for ComponentInformer. ", "error", err)
		return err
	}
	slog.Info("Shutting down informer...", "k8sClusterName", o.k8sClusterConfig.ClusterName)
	return nil
}

// OnUpdate 处理 opsRequest 更新事件
func (o *ComponentInformer) OnUpdate(_, newObj interface{}) {
	newUnstructured, ok := newObj.(*unstructured.Unstructured)
	if !ok {
		slog.Error("failed to cast newObj to Unstructured")
		return
	}

	var newComponent *appsv1.Component
	if err := runtime.DefaultUnstructuredConverter.FromUnstructured(
		newUnstructured.Object, &newComponent,
	); err != nil {
		slog.Error("failed to cast oldUnstructured to Component")
		return
	}
	clusterName := newComponent.Labels["app.kubernetes.io/instance"]
	componentName := newComponent.Name
	namespace := newComponent.GetNamespace()
	statusPhase := newComponent.Status.Phase
	clusterEntity, err := o.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		ClusterName:        clusterName,
		Namespace:          namespace,
		K8sClusterConfigID: o.k8sClusterConfig.ID,
	})
	if err != nil || clusterEntity == nil {
		slog.Error("failed to find cluster", "clusterName", clusterName, "namespace", namespace,
			"k8sClusterConfigID", o.k8sClusterConfig.ID, "err", err, "clusterEntity", clusterEntity)
		return
	}

	componentEntities, err := o.componentMetaProvider.FindComponentsByParams(&metaentity.ComponentQueryParams{
		ComponentName: componentName,
		CrdClusterID:  clusterEntity.ID,
	})
	if err != nil {
		slog.Error("failed to find component by name and cluster", "componentName", componentName,
			"crdClusterId", clusterEntity.ID, "err", err)
		return
	}
	if len(componentEntities) == 0 {
		slog.Warn("component does not exist", "crdClusterId", clusterEntity.ID, "componentName", componentName)
		return
	}
	if len(componentEntities) != 1 {
		slog.Warn("multiple component exists", "crdClusterId", clusterEntity.ID, "componentName", componentName)
		return
	}
	componentEntity := componentEntities[0]
	if componentEntity.Status != string(statusPhase) {
		slog.Info("component entity status changed",
			"component", componentName, "oldPhase", clusterEntity.Status, "newPhase", statusPhase)
		componentEntity.Status = string(statusPhase)
		_, err = o.componentMetaProvider.UpdateComponent(componentEntity)
		if err != nil {
			slog.Error("failed to update component entity",
				"component", componentName, "err", err)
			return
		}
	}
}
