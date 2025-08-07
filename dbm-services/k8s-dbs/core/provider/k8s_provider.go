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
	commtypes "k8s-dbs/common/types"
	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	coreutil "k8s-dbs/core/util"
	dbserrors "k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	metautil "k8s-dbs/metadata/util"
	"log/slog"
	"strings"
	"time"

	kbtypes "github.com/apecloud/kbcli/pkg/types"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// MaxPodLogLines pod log 返回最大行数
const MaxPodLogLines = 2000

// MaxPodLogSize pod log 返回最大字节数
const MaxPodLogSize = 5 * 1024 * 1024

// K8sProvider K8sProvider 结构体
type K8sProvider struct {
	reqRecordProvider     metaprovider.ClusterRequestRecordProvider
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
	clusterMetaProvider   metaprovider.K8sCrdClusterProvider
}

// DeletePod 删除 pod
func (k *K8sProvider) DeletePod(
	ctx *commentity.DbsContext,
	entity *coreentity.K8sPodDelete,
) error {
	k8sClusterConfig, err := k.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}
	ctx.K8sClusterConfigID = k8sClusterConfig.ID
	ctx.K8sClusterName = k8sClusterConfig.ClusterName
	ctx.Namespace = entity.Namespace
	ctx.ClusterName = entity.ClusterName
	// 记录审计日志
	_, err = metautil.SaveCommonAuditV2(k.reqRecordProvider, ctx, entity)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateMetaDataError, err)
	}

	ctx.K8sClusterConfigID = k8sClusterConfig.ID
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateK8sClientError, err)
	}
	deletePolicy := metav1.DeletePropagationForeground
	err = k8sClient.ClientSet.CoreV1().Pods(entity.Namespace).Delete(context.TODO(), entity.PodName, metav1.DeleteOptions{
		PropagationPolicy: &deletePolicy,
	})
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteK8sPodError, err)
	}

	// 更新集群 cluster 记录
	if err = metautil.UpdateClusterLastUpdatedV2(k.clusterMetaProvider, ctx); err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateMetaDataError, err)
	}
	return nil
}

// CreateNamespace 创建命名空间
func (k *K8sProvider) CreateNamespace(
	dbsContext *commentity.DbsContext,
	entity *coreentity.K8sNamespaceEntity,
) (*coreentity.K8sNamespaceEntity, error) {
	_, err := metautil.CreateRequestRecord(dbsContext, entity, coreconst.CreateK8sNs, k.reqRecordProvider)
	if err != nil {
		return nil, err
	}
	k8sClusterConfig, err := k.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}

	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
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
	// 创建命名空间资源
	createdNs, err := k8sClient.ClientSet.CoreV1().Namespaces().Create(context.TODO(), &ns, metav1.CreateOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to create namespace: %w", err)
	}

	// 创建命名空间配额
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

// GetPodRawLogs 获取 pod 原始日志
func (k *K8sProvider) GetPodRawLogs(entity *coreentity.K8sPodLogQueryParams) (string, error) {
	stream, err := k.buildLogStream(entity)
	if err != nil {
		return "", err
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

	logs, err := io.ReadAll(stream)
	return string(logs), err
}

// ListPodLogs 获取 pod 日志
func (k *K8sProvider) ListPodLogs(
	entity *coreentity.K8sPodLogQueryParams,
	pagination *entity.Pagination,
) ([]*coreentity.K8sLog, uint64, error) {
	stream, err := k.buildLogStream(entity)
	if err != nil {
		return nil, 0, err
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

// buildLogStream 构建日志流
func (k *K8sProvider) buildLogStream(entity *coreentity.K8sPodLogQueryParams) (io.ReadCloser, error) {
	k8sClusterConfig, err := k.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		return nil, err
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, err
	}

	// 构造日志选项
	logOptions := &corev1.PodLogOptions{
		Container:  entity.Container,
		Follow:     false,
		Timestamps: true,
		LimitBytes: commutil.Int64Ptr(MaxPodLogSize),
		TailLines:  commutil.Int64Ptr(MaxPodLogLines),
		Previous:   entity.Previous,
	}

	// 获取日志流
	podLogReq := k8sClient.ClientSet.CoreV1().Pods(entity.Namespace).GetLogs(entity.PodName, logOptions)
	stream, err := podLogReq.Stream(context.TODO())
	if err != nil {
		return nil, err
	}
	return stream, nil
}

// GetPodDetail 获取 pod 详情
func (k *K8sProvider) GetPodDetail(
	entity *coreentity.K8sPodDetailQueryParams,
) (*coreentity.K8sPodDetail, error) {
	k8sClusterConfig, err := k.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		return nil, err
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, err
	}
	crd := &coreentity.CustomResourceDefinition{
		ResourceName:         entity.PodName,
		Namespace:            entity.Namespace,
		GroupVersionResource: kbtypes.PodGVR(),
	}
	podCR, err := coreutil.GetCRD(k8sClient, crd)
	if err != nil {
		return nil, err
	}
	pod, err := coreutil.ConvertUnstructuredToPod(*podCR)
	if err != nil {
		return nil, err
	}
	var resourceQuota *coreentity.PodResourceQuota
	var resourceUsage *coreentity.PodResourceUsage
	if pod.Status.Phase == corev1.PodRunning {
		// 获取资源配额
		resourceQuota, err = coreutil.GetPodResourceQuota(k8sClient, pod)
		if err != nil {
			return nil, err
		}
		// 获取资源利用率
		var clusterMetaParams = &metaentity.ClusterQueryParams{
			K8sClusterConfigID: k8sClusterConfig.ID,
			Namespace:          entity.Namespace,
			ClusterName:        entity.ClusterName,
		}
		clusterMeta, err := k.clusterMetaProvider.FindByParams(clusterMetaParams)
		if err != nil {
			return nil, err
		}

		resourceUsage, err = coreutil.GetPodResourceUsage(clusterMeta.AddonInfo.AddonType,
			k8sClusterConfig.ClusterName, k8sClient, pod, resourceQuota)
		if err != nil {
			slog.Warn("failed to get pod resource usage", "namespace", pod.Namespace, "pod", pod.Name)
		}
	}
	podDetail := &coreentity.K8sPodDetail{
		K8sClusterName: entity.K8sClusterName,
		ClusterName:    entity.ClusterName,
		Namespace:      entity.Namespace,
		ComponentName:  pod.Labels["apps.kubeblocks.io/component-name"],
		Manifest:       commutil.MarshalToYAML(pod),
		Pod: &coreentity.Pod{
			PodName:       entity.PodName,
			Node:          pod.Spec.NodeName,
			Status:        pod.Status.Phase,
			Role:          coreutil.GetPodRole(pod),
			ResourceQuota: resourceQuota,
			ResourceUsage: resourceUsage,
			CreatedTime:   commtypes.JSONDatetime(pod.CreationTimestamp.Time),
		},
	}
	return podDetail, nil
}

// buildQuotaFromCreated 从 k8s quota 构建 ResourceQuota
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

// buildQuotaFromEntity 从 entity 构建资源配额
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

// validateResourceQuota 验证资源配额信息
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

// buildNsFromEntity 从 entity 构建 namespace
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

// readK8sPodLog 读取 pod 日志信息
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
			Timestamp: commtypes.JSONDatetime(timestamp),
			Message:   message,
		})
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("failed to read log stream: %w", err)
	}
	return k8sLogEntries, nil
}

// NewK8sProvider 创建 K8sProvider 实例
func NewK8sProvider(
	reqRecordProvider metaprovider.ClusterRequestRecordProvider,
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
) *K8sProvider {
	return &K8sProvider{
		reqRecordProvider,
		clusterConfigProvider,
		clusterMetaProvider,
	}
}
