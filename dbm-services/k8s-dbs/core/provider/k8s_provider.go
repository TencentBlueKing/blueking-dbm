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

package provider

import (
	"context"
	"fmt"
	coreclient "k8s-dbs/core/client"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/core/helper"
	pventity "k8s-dbs/core/provider/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// K8sProvider K8sProvider 结构体
type K8sProvider struct {
	reqRecordProvider     metaprovider.ClusterRequestRecordProvider
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
}

// CreateNamespace 创建命名空间
func (k *K8sProvider) CreateNamespace(entity *pventity.K8sNamespaceEntity) (*pventity.K8sNamespaceEntity, error) {

	_, err := helper.CreateRequestRecord(entity, coreconst.CreateK8sNs, k.reqRecordProvider)
	if err != nil {
		return nil, err
	}
	k8sClusterConfig, err := k.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}

	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	ns := k.buildNsFromEntity(entity)

	createdNs, err := k8sClient.ClientSet.CoreV1().Namespaces().Create(context.TODO(), &ns, metav1.CreateOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to create namespace: %w", err)
	}

	var resourceQuota *coreentity.ResourceQuota
	if entity.ResourceQuota != nil {
		quota, err := k.buildQuotaFromEntity(entity)
		if err != nil {
			slog.Error("failed to build resource quota", "error", err)
			return nil, err
		}
		createdQuota, err := k8sClient.ClientSet.CoreV1().
			ResourceQuotas(entity.Name).
			Create(context.TODO(), quota, metav1.CreateOptions{})
		if err != nil {
			return nil, fmt.Errorf("failed to create resourceQuota: %w", err)
		}
		resourceQuota = k.buildQuotaFromCreated(createdQuota)
	}

	responseEntity := pventity.K8sNamespaceEntity{
		K8sClusterName: entity.K8sClusterName,
		Name:           createdNs.Name,
		Annotations:    createdNs.Annotations,
		Labels:         createdNs.Labels,
		ResourceQuota:  resourceQuota,
	}

	return &responseEntity, nil
}

func (k *K8sProvider) buildQuotaFromCreated(
	createdQuota *corev1.ResourceQuota,
) *coreentity.ResourceQuota {
	cpuRequestQuantity := createdQuota.Spec.Hard[corev1.ResourceRequestsCPU]
	memoryRequestQuantity := createdQuota.Spec.Hard[corev1.ResourceRequestsMemory]
	cpuLimitQuantity := createdQuota.Spec.Hard[corev1.ResourceLimitsCPU]
	memoryLimitQuantity := createdQuota.Spec.Hard[corev1.ResourceLimitsMemory]
	return &coreentity.ResourceQuota{
		Request: coreentity.Resource{
			CPU:    cpuRequestQuantity.String(),
			Memory: memoryRequestQuantity.String(),
		},
		Limit: coreentity.Resource{
			CPU:    cpuLimitQuantity.String(),
			Memory: memoryLimitQuantity.String(),
		},
	}
}

func (k *K8sProvider) buildQuotaFromEntity(entity *pventity.K8sNamespaceEntity) (*corev1.ResourceQuota, error) {
	limitCPU, err := resource.ParseQuantity(entity.ResourceQuota.Limit.CPU)
	if err != nil {
		slog.Error("failed to parse resource quota limit CPU", "err", err)
		return nil, err
	}
	limitMemory, err := resource.ParseQuantity(entity.ResourceQuota.Limit.Memory)
	if err != nil {
		slog.Error("failed to parse resource quota limit Memory", "err", err)
		return nil, err
	}
	requestCPU, err := resource.ParseQuantity(entity.ResourceQuota.Request.CPU)
	if err != nil {
		slog.Error("failed to parse resource quota request CPU", "err", err)
		return nil, err
	}
	requestMemory, err := resource.ParseQuantity(entity.ResourceQuota.Request.Memory)
	if err != nil {
		slog.Error("failed to parse resource quota request Memory", "err", err)
		return nil, err
	}
	quota := corev1.ResourceQuota{
		ObjectMeta: metav1.ObjectMeta{
			Name:      entity.Name,
			Namespace: entity.Name,
		},
		Spec: corev1.ResourceQuotaSpec{
			Hard: map[corev1.ResourceName]resource.Quantity{
				corev1.ResourceLimitsCPU:      limitCPU,
				corev1.ResourceLimitsMemory:   limitMemory,
				corev1.ResourceRequestsCPU:    requestCPU,
				corev1.ResourceRequestsMemory: requestMemory,
			},
		},
	}
	return &quota, nil
}

func (k *K8sProvider) buildNsFromEntity(entity *pventity.K8sNamespaceEntity) corev1.Namespace {
	ns := corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:        entity.Name,
			Annotations: entity.Annotations,
			Labels:      entity.Labels,
		},
	}
	return ns
}

// NewK8sProvider 创建 K8sProviderImpl 实例
func NewK8sProvider(reqRecordProvider metaprovider.ClusterRequestRecordProvider,
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
) *K8sProvider {
	return &K8sProvider{
		reqRecordProvider,
		clusterConfigProvider,
	}
}
