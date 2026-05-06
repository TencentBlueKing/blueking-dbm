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
	"encoding/json"
	"fmt"
	"log/slog"

	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	coreerrors "k8s-dbs/errors"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// kubeletSummary 是 Kubelet Summary API 响应的最小化结构
type kubeletSummary struct {
	Pods []kubeletPodStats `json:"pods"`
}

type kubeletPodStats struct {
	PodRef  kubeletPodRef        `json:"podRef"`
	Volumes []kubeletVolumeStats `json:"volume"`
}

type kubeletPodRef struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace"`
}

type kubeletVolumeStats struct {
	Name      string  `json:"name"`
	UsedBytes *uint64 `json:"usedBytes"`
}

// QdrantClusterMetricFetcher 通过 Kubelet Summary API 获取 Qdrant 存储用量
type QdrantClusterMetricFetcher struct{}

// NewQdrantClusterMetricFetcher 创建 QdrantClusterMetricFetcher 实例
func NewQdrantClusterMetricFetcher() *QdrantClusterMetricFetcher {
	return &QdrantClusterMetricFetcher{}
}

// GetStorageUsage 获取 Qdrant Pod 的存储使用量，单位：GB
func (q *QdrantClusterMetricFetcher) GetStorageUsage(params *ClusterMetricQueryParams) (float64, error) {
	if params.K8sClient == nil {
		return 0, fmt.Errorf("qdrant metric fetcher requires K8sClient, but it is nil")
	}

	ctx, cancel := context.WithTimeoutCause(
		context.Background(),
		coreconst.K8sAPIServerTimeout,
		coreerrors.NewK8sDbsError(coreerrors.K8sAPIServerTimeoutError,
			fmt.Errorf("获取 Qdrant Pod %s/%s kubelet 指标超时", params.Namespace, params.PodName)),
	)
	defer cancel()

	nodeName, err := getPodNodeName(ctx, params.K8sClient, params.Namespace, params.PodName)
	if err != nil {
		return 0, fmt.Errorf("failed to get node name for pod %s/%s: %w", params.Namespace, params.PodName, err)
	}

	summary, err := fetchKubeletSummary(ctx, params.K8sClient, nodeName)
	if err != nil {
		return 0, fmt.Errorf("failed to fetch kubelet summary from node %s: %w", nodeName, err)
	}

	usedBytes, err := extractPodVolumeUsedBytes(summary, params.Namespace, params.PodName)
	if err != nil {
		return 0, fmt.Errorf("failed to extract volume usage for pod %s/%s: %w",
			params.Namespace, params.PodName, err)
	}

	storageGB := commutil.RoundToDecimal(commutil.ConvertByteToGB(float64(usedBytes)), 3)
	return storageGB, nil
}

// getPodNodeName 通过 K8s API 查询 Pod 所在节点名称
func getPodNodeName(ctx context.Context, k8sClient *commutil.K8sClient, namespace, podName string) (string, error) {
	pod, err := k8sClient.ClientSet.CoreV1().Pods(namespace).Get(ctx, podName, metav1.GetOptions{})
	if err != nil {
		return "", fmt.Errorf("get pod %s/%s failed: %w", namespace, podName, err)
	}
	if pod.Spec.NodeName == "" {
		return "", fmt.Errorf("pod %s/%s has no NodeName assigned", namespace, podName)
	}
	return pod.Spec.NodeName, nil
}

// fetchKubeletSummary 经由 kube-apiserver 代理调用 Kubelet Summary API
func fetchKubeletSummary(ctx context.Context, k8sClient *commutil.K8sClient, nodeName string) (*kubeletSummary, error) {
	rawData, err := k8sClient.ClientSet.CoreV1().RESTClient().Get().
		Resource("nodes").
		Name(nodeName).
		SubResource("proxy").
		Suffix("stats/summary").
		DoRaw(ctx)
	if err != nil {
		return nil, fmt.Errorf("kubelet summary API request failed for node %s: %w", nodeName, err)
	}

	var summary kubeletSummary
	if err := json.Unmarshal(rawData, &summary); err != nil {
		return nil, fmt.Errorf("failed to unmarshal kubelet summary response: %w", err)
	}
	return &summary, nil
}

// extractPodVolumeUsedBytes 从 kubelet summary 中提取指定 Pod 所有 Volume 的已用字节数之和
// 若某个 volume 的 usedBytes 为 nil（数据暂不可用），则安全跳过
func extractPodVolumeUsedBytes(summary *kubeletSummary, namespace, podName string) (uint64, error) {
	for _, pod := range summary.Pods {
		if pod.PodRef.Name != podName || pod.PodRef.Namespace != namespace {
			continue
		}
		var totalUsedBytes uint64
		for _, vol := range pod.Volumes {
			if vol.UsedBytes == nil {
				slog.Warn("volume used bytes is nil", "volume", vol.Name)
				continue
			}
			totalUsedBytes += *vol.UsedBytes
		}
		return totalUsedBytes, nil
	}
	return 0, fmt.Errorf("pod %s/%s not found in kubelet summary", namespace, podName)
}
