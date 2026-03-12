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
	"encoding/json"
	"fmt"
	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"
	"strings"
	"time"

	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/informers"
	"k8s.io/client-go/tools/cache"
)

// ServiceInformer 使用 typed corev1 SharedInformerFactory 监听 K8s Service 变化
// 并将服务信息同步到 tb_k8s_cluster_service
type ServiceInformer struct {
	k8sClusterConfig       *metaentity.K8sClusterConfigEntity
	clusterMetaProvider    metaprovider.K8sCrdClusterProvider
	clusterServiceProvider metaprovider.K8sClusterServiceProvider
}

// NewServiceInformer 创建 ServiceInformer 实例
func NewServiceInformer(
	k8sClusterConfig *metaentity.K8sClusterConfigEntity,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	clusterServiceProvider metaprovider.K8sClusterServiceProvider,
) *ServiceInformer {
	return &ServiceInformer{
		k8sClusterConfig:       k8sClusterConfig,
		clusterMetaProvider:    clusterMetaProvider,
		clusterServiceProvider: clusterServiceProvider,
	}
}

// Start 启动 ServiceInformer，使用 typed corev1 SharedInformerFactory
func (s *ServiceInformer) Start(ctx context.Context) error {
	slog.Info("Starting ServiceInformer...", "k8sClusterName", s.k8sClusterConfig.ClusterName)

	k8sClient, err := commutil.NewK8sClient(s.k8sClusterConfig)
	if err != nil {
		return errors.Wrap(err, "failed to create k8s client")
	}

	// 创建带 label 过滤的 typed SharedInformerFactory
	labelSelector := coreconst.ManagedBy + "=" + coreconst.Kubeblocks
	factory := informers.NewSharedInformerFactoryWithOptions(
		k8sClient.ClientSet,
		30*time.Second,
		informers.WithTweakListOptions(func(opts *metav1.ListOptions) {
			opts.LabelSelector = labelSelector
		}),
	)

	serviceInformer := factory.Core().V1().Services().Informer()

	_, err = serviceInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc:    s.onAddOrUpdate,
		UpdateFunc: func(_, newObj interface{}) { s.onAddOrUpdate(newObj) },
		DeleteFunc: s.onDelete,
	})
	if err != nil {
		return errors.Wrap(err, "failed to add event handler")
	}

	// 启动 informer
	go serviceInformer.Run(ctx.Done())

	// 等待缓存同步
	syncCtx, syncCancel := context.WithTimeout(ctx, 60*time.Second)
	defer syncCancel()

	if !cache.WaitForCacheSync(syncCtx.Done(), serviceInformer.HasSynced) {
		return errors.New("ServiceInformer cache sync timed out")
	}

	slog.Info("ServiceInformer started and cache synced",
		"k8sClusterName", s.k8sClusterConfig.ClusterName)

	// 等待终止信号
	<-ctx.Done()
	slog.Info("Shutting down ServiceInformer...", "k8sClusterName", s.k8sClusterConfig.ClusterName)
	return nil
}

// onAddOrUpdate 处理 Service 创建和更新事件
func (s *ServiceInformer) onAddOrUpdate(obj interface{}) {
	service, ok := obj.(*corev1.Service)
	if !ok {
		slog.Error("ServiceInformer: failed to cast obj to *corev1.Service")
		return
	}

	clusterName, componentName, ok := s.extractLabels(service)
	if !ok {
		return
	}

	clusterEntity, err := s.findClusterEntity(clusterName, service.Namespace)
	if err != nil || clusterEntity == nil {
		return
	}

	entity := s.buildServiceEntity(service, clusterEntity.ID, componentName)

	// 使用事务性 per-service upsert: 原子性地删除旧记录并插入新记录
	if err := s.clusterServiceProvider.UpsertSingleService(entity); err != nil {
		slog.Error("ServiceInformer: failed to upsert service record",
			"service", service.Name, "error", err)
	}
}

// onDelete 处理 Service 删除事件
func (s *ServiceInformer) onDelete(obj interface{}) {
	service, ok := obj.(*corev1.Service)
	if !ok {
		// 尝试从 DeletedFinalStateUnknown 中获取
		tombstone, ok := obj.(cache.DeletedFinalStateUnknown)
		if !ok {
			slog.Error("ServiceInformer: failed to cast deleted obj")
			return
		}
		service, ok = tombstone.Obj.(*corev1.Service)
		if !ok {
			slog.Error("ServiceInformer: failed to cast tombstone obj to *corev1.Service")
			return
		}
	}

	clusterName, _, ok := s.extractLabels(service)
	if !ok {
		return
	}

	clusterEntity, err := s.findClusterEntity(clusterName, service.Namespace)
	if err != nil || clusterEntity == nil {
		return
	}

	if _, err := s.clusterServiceProvider.DeleteByClusterIDAndServiceName(
		clusterEntity.ID, service.Name,
	); err != nil {
		slog.Warn("ServiceInformer: failed to delete service record on service deletion",
			"service", service.Name, "error", err)
	}
}

// extractLabels 从 Service 的 labels 中提取 clusterName 和 componentName
// 返回 false 表示该 Service 不是 KubeBlocks 管理的服务
// componentName 可能为空（如 Expose 创建的 Service 不带 component-name 标签）
func (s *ServiceInformer) extractLabels(service *corev1.Service) (string, string, bool) {
	labels := service.Labels
	if labels == nil {
		return "", "", false
	}

	clusterName := labels[coreconst.InstanceName]
	if clusterName == "" {
		return "", "", false
	}

	componentName := labels[coreconst.ComponentName]
	return clusterName, componentName, true
}

// findClusterEntity 根据集群名称和命名空间查找集群实体
func (s *ServiceInformer) findClusterEntity(
	clusterName, namespace string,
) (*metaentity.K8sCrdClusterEntity, error) {
	entity, err := s.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		ClusterName:        clusterName,
		Namespace:          namespace,
		K8sClusterConfigID: s.k8sClusterConfig.ID,
	})
	if err != nil {
		slog.Debug("ServiceInformer: failed to find cluster entity",
			"cluster", clusterName, "namespace", namespace, "error", err)
		return nil, err
	}
	if entity == nil {
		slog.Debug("ServiceInformer: cluster entity not found, skipping",
			"cluster", clusterName, "namespace", namespace)
	}
	return entity, nil
}

// buildServiceEntity 从 K8s Service 对象构建 K8sClusterServiceEntity
func (s *ServiceInformer) buildServiceEntity(
	service *corev1.Service,
	crdClusterID uint64,
	componentName string,
) *metaentity.K8sClusterServiceEntity {
	entity := &metaentity.K8sClusterServiceEntity{
		CrdClusterID:  crdClusterID,
		ComponentName: componentName,
		ServiceName:   service.Name,
		ServiceType:   string(service.Spec.Type),
		CreatedBy:     coreconst.DefaultUserName,
		UpdatedBy:     coreconst.DefaultUserName,
	}

	// 序列化 annotations
	if len(service.Annotations) > 0 {
		annotationsJSON, err := json.Marshal(service.Annotations)
		if err == nil {
			entity.Annotations = string(annotationsJSON)
		}
	}

	// 内部地址：fqdn:port 格式
	fqdn := fmt.Sprintf("%s.%s.svc.cluster.local", service.Name, service.Namespace)
	var internalAddrs []string
	for _, port := range service.Spec.Ports {
		internalAddrs = append(internalAddrs, fmt.Sprintf("%s:%d", fqdn, port.Port))
	}
	entity.InternalAddrs = strings.Join(internalAddrs, ",")

	// 外部地址：仅 LoadBalancer 类型
	if service.Spec.Type == corev1.ServiceTypeLoadBalancer && len(service.Status.LoadBalancer.Ingress) > 0 {
		ingress := service.Status.LoadBalancer.Ingress[0]
		host := ingress.IP
		if host == "" {
			host = ingress.Hostname
		}
		var externalAddrs []string
		for _, port := range service.Spec.Ports {
			externalAddrs = append(externalAddrs, fmt.Sprintf("%s:%d", host, port.Port))
		}
		entity.ExternalAddrs = strings.Join(externalAddrs, ",")
	}

	return entity
}
