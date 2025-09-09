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
	"fmt"
	commconst "k8s-dbs/common/constant"
	"k8s-dbs/common/types"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"
	"time"

	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
	"github.com/pkg/errors"
	"k8s.io/client-go/dynamic/dynamicinformer"
	"k8s.io/client-go/tools/cache"
)

// OpsRequestInformer OpsRequest informer 结构体
type OpsRequestInformer struct {
	k8sClusterConfig       *metaentity.K8sClusterConfigEntity
	clusterMetaProvider    metaprovider.K8sCrdClusterProvider
	opsRequestMetaProvider metaprovider.K8sCrdOpsRequestProvider
}

// NewOpsRequestInformer OpsRequest informer 构造函数
func NewOpsRequestInformer(
	k8sClusterConfig *metaentity.K8sClusterConfigEntity,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	opsRequestMetaProvider metaprovider.K8sCrdOpsRequestProvider,
) *OpsRequestInformer {
	return &OpsRequestInformer{
		k8sClusterConfig:       k8sClusterConfig,
		clusterMetaProvider:    clusterMetaProvider,
		opsRequestMetaProvider: opsRequestMetaProvider,
	}
}

// Start 启动
func (o *OpsRequestInformer) Start(
	ctx context.Context,
	factory dynamicinformer.DynamicSharedInformerFactory,
) error {
	slog.Info("Starting informer...", "k8sClusterName", o.k8sClusterConfig.ClusterName)
	genericOpsInformer := factory.ForResource(kbtypes.OpsGVR())

	opsInformer := genericOpsInformer.Informer()
	_, err := opsInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		UpdateFunc: o.OnUpdate,
	})
	if err != nil {
		return errors.Wrap(err, "failed to add OpsRequest handler")
	}

	go opsInformer.Run(ctx.Done())

	go func() {
		ticker := time.NewTicker(30 * time.Second)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				slog.Info("waiting for cache sync... Synced", "synced", opsInformer.HasSynced())
			case <-ctx.Done():
				return
			}
		}
	}()

	syncCtx, syncCancel := context.WithTimeout(ctx, 30*time.Second)
	defer syncCancel()

	if !cache.WaitForCacheSync(syncCtx.Done(), opsInformer.HasSynced) {
		if errors.Is(syncCtx.Err(), context.DeadlineExceeded) {
			slog.Error("OpsInformer cache sync timed out after 30 seconds")
			return errors.New("OpsInformer cache sync timed out after 30 seconds")
		}
		return errors.New("timed out waiting for caches to sync")
	}
	slog.Info("OpsRequest Informer started and cache synced")
	// 等待终止信号
	<-ctx.Done()
	slog.Info("Shutting down informer...")
	return nil
}

// OnUpdate 处理 opsRequest 更新事件
func (o *OpsRequestInformer) OnUpdate(_, newObj interface{}) {
	newUnstructured, ok := newObj.(*unstructured.Unstructured)
	if !ok {
		slog.Error("failed to cast newObj to Unstructured")
		return
	}

	var newOpsRequest *opv1.OpsRequest
	if err := runtime.
		DefaultUnstructuredConverter.FromUnstructured(newUnstructured.Object, &newOpsRequest); err != nil {
		slog.Error("failed to cast oldUnstructured to OpsRequest")
		return
	}
	clusterName := newOpsRequest.Spec.ClusterName
	opsRequestName := newOpsRequest.GetName()
	nameSpace := newOpsRequest.GetNamespace()
	status := newOpsRequest.Status
	completionTime := status.CompletionTimestamp
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
	opsRequestEntities, err := o.opsRequestMetaProvider.FindOpsRequestByParams(&metaentity.OpsRequestQueryParams{
		CrdClusterID:       clusterEntity.ID,
		K8sClusterConfigID: o.k8sClusterConfig.ID,
		OpsRequestName:     opsRequestName,
	})
	if err != nil || len(opsRequestEntities) != 1 {
		slog.Error("failed to find opsRequest", "OpsRequestName", opsRequestName, "err", err)
		return
	}
	opsRequestEntity := opsRequestEntities[0]
	if opsRequestEntity.Status != string(status.Phase) {
		slog.Info("opsRequest entity status changed", "opsRequestName", opsRequestName,
			"clusterName", clusterName, "oldPhase", opsRequestEntity.Status, "newPhase", status.Phase)
		opsRequestEntity.Status = string(status.Phase)
		opsRequestEntity.UpdatedBy = commconst.SystemUser
		if !completionTime.IsZero() {
			t := types.JSONDatetime(completionTime.Time)
			opsRequestEntity.CompletedAt = &t
		}
		_, err = o.opsRequestMetaProvider.UpdateOpsRequest(opsRequestEntity)
		if err != nil {
			slog.Error("failed to update opsRequest entity", "opsRequestName", opsRequestName,
				"clusterName", clusterName, "err", err)
			return
		}
	}
}
