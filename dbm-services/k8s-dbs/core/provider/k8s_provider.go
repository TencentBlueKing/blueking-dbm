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
	"bufio"
	"context"
	"fmt"
	"io"
	"k8s-dbs/common/entity"
	commentity "k8s-dbs/common/entity"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/core/helper"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"
	"strings"
	"time"

	commutil "k8s-dbs/common/util"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

const MaxPodLogLines = 2000
const MaxPodLogSize = 5 * 1024 * 1024

// K8sProvider K8sProvider 结构体
type K8sProvider struct {
	reqRecordProvider     metaprovider.ClusterRequestRecordProvider
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
}

// CreateNamespace 创建命名空间
func (k *K8sProvider) CreateNamespace(
	dbsContext *commentity.DbsContext,
	entity *coreentity.K8sNamespaceEntity,
) (*coreentity.K8sNamespaceEntity, error) {
	_, err := helper.CreateRequestRecord(dbsContext, entity, coreconst.CreateK8sNs, k.reqRecordProvider)
	if err != nil {
		return nil, err
	}
	k8sClusterConfig, err := k.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}

	k8sClient, err := helper.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	if entity.ResourceQuota != nil {
		if err = k.validateResourceQuota(entity); err != nil {
			slog.Error("failed to validate resource quota format", "err", err)
			return nil, fmt.Errorf("failed to validate resource quota format: %w", err)
		}
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

	responseEntity := coreentity.K8sNamespaceEntity{
		K8sClusterName: entity.K8sClusterName,
		Name:           createdNs.Name,
		Annotations:    createdNs.Annotations,
		Labels:         createdNs.Labels,
		ResourceQuota:  resourceQuota,
	}

	return &responseEntity, nil
}

// ListPodLogs 获取 pod 日志
func (k *K8sProvider) ListPodLogs(
	entity *coreentity.K8sPodLogEntity,
	pagination *entity.Pagination,
) ([]*coreentity.K8sLog, uint64, error) {
	// 1. 获取集群配置
	k8sClusterConfig, err := k.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to get k8sClusterConfig for cluster %q: %w", entity.K8sClusterName, err)
	}

	// 2. 创建 Kubernetes Client
	k8sClient, err := helper.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to create k8sClient for cluster %q: %w", entity.K8sClusterName, err)
	}

	// 3. 构造日志选项
	logOptions := &corev1.PodLogOptions{
		Container:  entity.Container,
		Follow:     false,
		Timestamps: true,
		LimitBytes: commutil.Int64Ptr(MaxPodLogSize),
		TailLines:  commutil.Int64Ptr(MaxPodLogLines),
	}

	// 4. 获取日志流
	podLogReq := k8sClient.ClientSet.CoreV1().Pods(entity.Namespace).GetLogs(entity.PodName, logOptions)
	stream, err := podLogReq.Stream(context.TODO())
	if err != nil {
		return nil, 0, fmt.Errorf("failed to stream logs for pod %q in namespace %q: %w",
			entity.PodName, entity.Namespace, err)
	}
	defer func() {
		if err := stream.Close(); err != nil {
			slog.Error("failed to close log stream",
				"namespace", entity.Namespace,
				"pod", entity.PodName,
				"err", err,
			)
		}
	}()

	logs, err := k.readK8sPodLog(stream)
	if err != nil {
		return nil, 0, err
	}
	count := uint64(len(logs))
	if pagination == nil {
		return logs, count, nil
	}
	logs, err = commutil.Paginate(pagination, logs)
	if err != nil {
		return nil, 0, err
	}
	return logs, count, nil

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
			CPU:    cpuRequestQuantity,
			Memory: memoryRequestQuantity,
		},
		Limit: coreentity.Resource{
			CPU:    cpuLimitQuantity,
			Memory: memoryLimitQuantity,
		},
	}
}

func (k *K8sProvider) buildQuotaFromEntity(entity *coreentity.K8sNamespaceEntity) (*corev1.ResourceQuota, error) {
	quota := corev1.ResourceQuota{
		ObjectMeta: metav1.ObjectMeta{
			Name:      entity.Name,
			Namespace: entity.Name,
		},
		Spec: corev1.ResourceQuotaSpec{
			Hard: map[corev1.ResourceName]resource.Quantity{
				corev1.ResourceLimitsCPU:      entity.ResourceQuota.Limit.CPU,
				corev1.ResourceLimitsMemory:   entity.ResourceQuota.Limit.Memory,
				corev1.ResourceRequestsCPU:    entity.ResourceQuota.Request.CPU,
				corev1.ResourceRequestsMemory: entity.ResourceQuota.Request.Memory,
			},
		},
	}
	return &quota, nil
}

func (k *K8sProvider) validateResourceQuota(entity *coreentity.K8sNamespaceEntity) error {
	if entity.ResourceQuota.Limit.CPU.IsZero() {
		slog.Error("invalid resource quota: CPU limit cannot be zero", "namespace", entity.Name)
		return fmt.Errorf("invalid resource quota: CPU limit cannot be zero (namespace=%s)", entity.Name)
	}
	if entity.ResourceQuota.Limit.Memory.IsZero() {
		slog.Error("invalid resource quota: Memory limit cannot be zero", "namespace", entity.Name)
		return fmt.Errorf("invalid resource quota: Memory limit cannot be zero (namespace=%s)", entity.Name)
	}
	if entity.ResourceQuota.Request.CPU.IsZero() {
		slog.Error("invalid resource quota: CPU request cannot be zero", "namespace", entity.Name)
		return fmt.Errorf("invalid resource quota: CPU request cannot be zero (namespace=%s)", entity.Name)
	}
	if entity.ResourceQuota.Request.Memory.IsZero() {
		slog.Error("invalid resource quota: Memory request cannot be zero", "namespace", entity.Name)
		return fmt.Errorf("invalid resource quota: Memory request cannot be zero (namespace=%s)", entity.Name)
	}
	return nil
}

func (k *K8sProvider) buildNsFromEntity(entity *coreentity.K8sNamespaceEntity) corev1.Namespace {
	ns := corev1.Namespace{
		ObjectMeta: metav1.ObjectMeta{
			Name:        entity.Name,
			Annotations: entity.Annotations,
			Labels:      entity.Labels,
		},
	}
	return ns
}

func (k *K8sProvider) readK8sPodLog(stream io.ReadCloser) ([]*coreentity.K8sLog, error) {
	var k8sLogEntries []*coreentity.K8sLog
	scanner := bufio.NewScanner(stream)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, " ", 2)
		if len(parts) != 2 {
			continue
		}
		timestampStr, message := parts[0], parts[1]
		timestamp, err := time.Parse(time.RFC3339Nano, timestampStr)
		if err != nil {
			continue
		}
		k8sLogEntries = append(k8sLogEntries, &coreentity.K8sLog{
			Timestamp: timestamp,
			Message:   message,
		})
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("failed to read log stream: %w", err)
	}
	return k8sLogEntries, nil
}

// NewK8sProvider 创建 K8sProvider 实例
func NewK8sProvider(reqRecordProvider metaprovider.ClusterRequestRecordProvider,
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
) *K8sProvider {
	return &K8sProvider{
		reqRecordProvider,
		clusterConfigProvider,
	}
}
