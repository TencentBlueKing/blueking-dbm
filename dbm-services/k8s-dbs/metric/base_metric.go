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

package metric

import (
	"context"
	"fmt"

	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	coreerrors "k8s-dbs/errors"
	metricutil "k8s-dbs/metric/util"
)

// BaseKubeletMetricFetcher 基于 Kubelet Summary API 的指标采集基类，
// 封装了"按 Pod 维度采集存储使用量"的默认流水线，供各 addon Fetcher 嵌入复用。
// 需要特殊逻辑时（如跨 Pod 聚合），在子类覆盖 GetStorageUsage 即可。
type BaseKubeletMetricFetcher struct {
	// AddonName 用于日志与错误文案，如 "Qdrant" / "SurrealDB"
	AddonName string
}

// NewBaseKubeletMetricFetcher 构造基类实例
func NewBaseKubeletMetricFetcher(addonName string) BaseKubeletMetricFetcher {
	return BaseKubeletMetricFetcher{AddonName: addonName}
}

// GetPodStorageGB 采集单个 Pod 的存储使用量，单位 GB，保留 3 位小数
func (b *BaseKubeletMetricFetcher) GetPodStorageGB(
	k8sClient *commutil.K8sClient,
	namespace, podName string,
) (float64, error) {
	if k8sClient == nil {
		return 0, fmt.Errorf("%s metric fetcher requires K8sClient, but it is nil", b.AddonName)
	}

	ctx, cancel := context.WithTimeoutCause(
		context.Background(),
		coreconst.K8sAPIServerTimeout,
		coreerrors.NewK8sDbsError(coreerrors.K8sAPIServerTimeoutError,
			fmt.Errorf("获取 %s Pod %s/%s kubelet 指标超时", b.AddonName, namespace, podName)),
	)
	defer cancel()

	nodeName, err := metricutil.GetPodNodeName(ctx, k8sClient, namespace, podName)
	if err != nil {
		return 0, fmt.Errorf("failed to get node name for pod %s/%s: %w", namespace, podName, err)
	}

	summary, err := metricutil.FetchKubeletSummary(ctx, k8sClient, nodeName)
	if err != nil {
		return 0, fmt.Errorf("failed to fetch kubelet summary from node %s: %w", nodeName, err)
	}

	usedBytes, err := metricutil.ExtractPodVolumeUsedBytes(summary, namespace, podName)
	if err != nil {
		return 0, fmt.Errorf("failed to extract volume usage for pod %s/%s: %w", namespace, podName, err)
	}

	storageGB := commutil.RoundToDecimal(commutil.ConvertByteToGB(float64(usedBytes)), 3)
	return storageGB, nil
}

// GetStorageUsage 默认按 params.PodName 走单 Pod 采集路径，实现 ClusterMetricFetcher 接口
func (b *BaseKubeletMetricFetcher) GetStorageUsage(params *ClusterMetricQueryParams) (float64, error) {
	return b.GetPodStorageGB(params.K8sClient, params.Namespace, params.PodName)
}
