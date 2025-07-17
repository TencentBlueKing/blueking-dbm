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

package helper

import (
	"context"
	"encoding/json"
	"fmt"
	commentity "k8s-dbs/common/entity"
	helper2 "k8s-dbs/common/helper"
	"k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	coreerrors "k8s-dbs/errors"

	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"

	providerentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	"helm.sh/helm/v3/pkg/action"
)

// CreateRequestRecord Save request
func CreateRequestRecord(
	dbsContext *commentity.DbsContext,
	requestParams interface{},
	requestType string,
	reqRecordProvider metaprovider.ClusterRequestRecordProvider,
) (*providerentity.ClusterRequestRecordEntity, error) {
	if requestParams == nil {
		return nil, fmt.Errorf("requestParams is nil")
	}

	if requestType == "" {
		return nil, fmt.Errorf("requestType is empty")
	}
	serializedRequest, err := json.Marshal(requestParams)
	if err != nil {
		return nil, fmt.Errorf("failed to serialize request parameters: %w", err)
	}

	requestRecord := &providerentity.ClusterRequestRecordEntity{
		RequestID:     util.RequestID(),
		RequestType:   requestType,
		RequestParams: string(serializedRequest),
		CreatedBy:     dbsContext.BkAuth.BkUserName,
		UpdatedBy:     dbsContext.BkAuth.BkUserName,
	}
	addedRequestRecord, err := reqRecordProvider.CreateRequestRecord(requestRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create request record entity: %w", err)
	}
	return addedRequestRecord, nil
}

// BuildHelmActionConfig 构建 helm action config
func BuildHelmActionConfig(
	namespace string,
	k8sClient *helper2.K8sClient,
) (*action.Configuration, error) {
	actionConfig, err := k8sClient.BuildHelmConfig(namespace)
	if err != nil {
		slog.Error("failed to build Helm configuration",
			"namespace", namespace,
			"error", err,
		)
		return nil, fmt.Errorf("failed to build Helm configuration for namespace %q: %w",
			namespace, err)
	}
	return actionConfig, nil
}

// SaveAuditLog 记录审计日志
func SaveAuditLog(
	reqRecordProvider metaprovider.ClusterRequestRecordProvider,
	request *coreentity.Request,
	requestType string,
) (*providerentity.ClusterRequestRecordEntity, error) {
	requestBytes, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("serialization request failed: %v", err)
	}

	requestRecord := &providerentity.ClusterRequestRecordEntity{
		K8sClusterName: request.K8sClusterName,
		ClusterName:    request.ClusterName,
		NameSpace:      request.Namespace,
		RequestID:      util.RequestID(),
		RequestType:    requestType,
		RequestParams:  string(requestBytes),
		CreatedBy:      request.BKAuth.BkUserName,
		UpdatedBy:      request.BKAuth.BkUserName,
	}

	addedRequestRecord, err := reqRecordProvider.CreateRequestRecord(requestRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create request entity: %w", err)
	}
	return addedRequestRecord, nil
}

// GetPodStorageCapacity 获取 pod 存储容量大小，单位：GB
func GetPodStorageCapacity(k8sClient *helper2.K8sClient, pod *corev1.Pod) (*coreentity.StorageSize, error) {
	volumes := pod.Spec.Volumes
	if len(volumes) == 0 {
		return nil, nil
	}
	var pvcName string
	for _, volume := range volumes {
		// 只取第一个
		if volume.PersistentVolumeClaim != nil {
			pvcName = volume.PersistentVolumeClaim.ClaimName
			break
		}
	}
	if pvcName == "" {
		return nil, nil
	}
	ctx, cancel := context.WithTimeoutCause(
		context.Background(),
		coreconst.K8sAPIServerTimeout,
		coreerrors.NewK8sDbsError(coreerrors.K8sAPIServerTimeoutError, fmt.Errorf("获取 PVC %s 超时", pvcName)),
	)
	defer cancel()

	pvc, err := k8sClient.ClientSet.CoreV1().PersistentVolumeClaims(pod.Namespace).Get(
		ctx,
		pvcName,
		metav1.GetOptions{},
	)
	if err != nil {
		if errors.Is(err, context.DeadlineExceeded) {
			slog.Error("获取 PVC 超时", "pvcName", pvcName, "podName", pod.Name, "error", err)
		} else {
			slog.Error("获取 PVC 失败", "pvcName", pvcName, "podName", pod.Name, "error", err)
		}
		return nil, err
	}
	capacity, ok := pvc.Spec.Resources.Requests[corev1.ResourceStorage]
	if !ok {
		return nil, nil
	}
	storageSize := coreentity.StorageSize(util.ConvertMemoryToGB(&capacity))
	return &storageSize, nil
}

// GetPodResourceQuota 从 Pod 的容器中提取资源请求和限制
func GetPodResourceQuota(k8sClient *helper2.K8sClient, pod *corev1.Pod) (*coreentity.PodResourceQuota, error) {
	if len(pod.Spec.Containers) == 0 {
		return nil, fmt.Errorf("pod %s has no containers", pod.Name)
	}
	container := pod.Spec.Containers[0]
	requestMemory := container.Resources.Requests.Memory()
	requestCPU := container.Resources.Requests.Cpu()
	limitMemory := container.Resources.Limits.Memory()
	limitCPU := container.Resources.Limits.Cpu()
	storage, _ := GetPodStorageCapacity(k8sClient, pod)
	return &coreentity.PodResourceQuota{
		Request: &coreentity.QuotaSummary{
			CPU:    util.Float64Ptr(util.ConvertCPUToCores(requestCPU)),
			Memory: util.Float64Ptr(util.ConvertMemoryToGB(requestMemory)),
		},
		Limit: &coreentity.QuotaSummary{
			CPU:    util.Float64Ptr(util.ConvertCPUToCores(limitCPU)),
			Memory: util.Float64Ptr(util.ConvertMemoryToGB(limitMemory)),
		},
		Storage: storage,
	}, nil
}

// ConvertUnstructuredToPod 将 Unstructured 对象转换为 Pod 类型
func ConvertUnstructuredToPod(item unstructured.Unstructured) (*corev1.Pod, error) {
	pod := &corev1.Pod{}
	if err := runtime.DefaultUnstructuredConverter.FromUnstructured(item.Object, pod); err != nil {
		return nil, fmt.Errorf("cannot convert to Pod format: %w", err)
	}
	return pod, nil
}

// GetPodResourceUsage 获取 Pod 资源利用率
func GetPodResourceUsage(
	k8sClient *helper2.K8sClient,
	pod *corev1.Pod,
	resourceQuota *coreentity.PodResourceQuota,
) (*coreentity.PodResourceUsage, error) {
	podMetrics, err := k8sClient.MetricsClient.
		MetricsV1beta1().PodMetricses(pod.Namespace).Get(context.TODO(), pod.Name, metav1.GetOptions{})
	if err != nil {
		panic(err.Error())
	}
	var totalCPU resource.Quantity
	var totalMemory resource.Quantity
	for _, container := range podMetrics.Containers {
		totalCPU.Add(*container.Usage.Cpu())
		totalMemory.Add(*container.Usage.Memory())
	}

	totalCPUCore := util.ConvertCPUToCores(&totalCPU)
	totalMemoryGB := util.ConvertMemoryToGB(&totalMemory)

	totalCPUCore = util.RoundToDecimal(totalCPUCore, 3)
	totalMemoryGB = util.RoundToDecimal(totalMemoryGB, 3)

	cpuUtilization := totalCPUCore / *resourceQuota.Request.CPU * 100
	cpuUtilization = util.RoundToDecimal(cpuUtilization, 3)

	memoryUtilization := totalMemoryGB / *resourceQuota.Request.Memory * 100
	memoryUtilization = util.RoundToDecimal(memoryUtilization, 3)

	return &coreentity.PodResourceUsage{
		QuotaSummary: &coreentity.QuotaSummary{
			CPU:     &totalCPUCore,
			Memory:  &totalMemoryGB,
			Storage: nil, // 待补充
		},
		CPUPercent:     &cpuUtilization,
		MemoryPercent:  &memoryUtilization,
		StoragePercent: nil, // 待补充
	}, nil
}
