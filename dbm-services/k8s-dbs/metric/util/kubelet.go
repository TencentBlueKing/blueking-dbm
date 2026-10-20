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

// Package util 提供 metric 模块共享的通用工具。
package util

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"

	commutil "k8s-dbs/common/util"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// KubeletSummary 是 Kubelet Summary API 响应的最小化结构
type KubeletSummary struct {
	Pods []KubeletPodStats `json:"pods"`
}

// KubeletPodStats 单个 Pod 的统计信息
type KubeletPodStats struct {
	PodRef  KubeletPodRef        `json:"podRef"`
	Volumes []KubeletVolumeStats `json:"volume"`
}

// KubeletPodRef Pod 引用信息
type KubeletPodRef struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace"`
}

// KubeletPVCRef Volume 对应的 PVC 引用，仅 PVC 挂载的 volume 才有
type KubeletPVCRef struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace"`
}

// KubeletVolumeStats 单个 Volume 的统计信息
// 注意：Block 模式 PVC（volumeMode: Block）无文件系统，不会上报 usedBytes。
type KubeletVolumeStats struct {
	Name           string         `json:"name"`
	UsedBytes      *uint64        `json:"usedBytes"`
	CapacityBytes  *uint64        `json:"capacityBytes,omitempty"`
	AvailableBytes *uint64        `json:"availableBytes,omitempty"`
	InodesUsed     *uint64        `json:"inodesUsed,omitempty"`
	Inodes         *uint64        `json:"inodes,omitempty"`
	PvcRef         *KubeletPVCRef `json:"pvcRef,omitempty"`
}

// IsPVC 返回该 volume 是否由 PVC 挂载
func (v *KubeletVolumeStats) IsPVC() bool {
	return v.PvcRef != nil
}

// GetPodNodeName 查询 Pod 所在节点名称
func GetPodNodeName(ctx context.Context, k8sClient *commutil.K8sClient, namespace, podName string) (string, error) {
	pod, err := k8sClient.ClientSet.CoreV1().Pods(namespace).Get(ctx, podName, metav1.GetOptions{})
	if err != nil {
		return "", fmt.Errorf("get pod %s/%s failed: %w", namespace, podName, err)
	}
	if pod.Spec.NodeName == "" {
		return "", fmt.Errorf("pod %s/%s has no NodeName assigned", namespace, podName)
	}
	return pod.Spec.NodeName, nil
}

// FetchKubeletSummary 经由 kube-apiserver 代理调用 Kubelet Summary API
func FetchKubeletSummary(ctx context.Context, k8sClient *commutil.K8sClient, nodeName string) (*KubeletSummary, error) {
	rawData, err := k8sClient.ClientSet.CoreV1().RESTClient().Get().
		Resource("nodes").
		Name(nodeName).
		SubResource("proxy").
		Suffix("stats/summary").
		DoRaw(ctx)
	if err != nil {
		return nil, fmt.Errorf("kubelet summary API request failed for node %s: %w", nodeName, err)
	}

	var summary KubeletSummary
	if err := json.Unmarshal(rawData, &summary); err != nil {
		return nil, fmt.Errorf("failed to unmarshal kubelet summary response: %w", err)
	}
	return &summary, nil
}

// ExtractPodVolumeUsedBytes 累加指定 Pod 下所有 PVC Volume 的已用字节数。
// 非 PVC volume（configMap/secret/emptyDir/projected 等）会被跳过；
// usedBytes 为 nil 时打 warn 日志并跳过；Pod 不存在时返回错误。
func ExtractPodVolumeUsedBytes(summary *KubeletSummary, namespace, podName string) (uint64, error) {
	for _, pod := range summary.Pods {
		if pod.PodRef.Name != podName || pod.PodRef.Namespace != namespace {
			continue
		}
		var totalUsedBytes uint64
		for _, vol := range pod.Volumes {
			if !vol.IsPVC() {
				continue
			}
			if vol.UsedBytes == nil {
				slog.Warn("pvc volume used bytes is nil",
					"volume", vol.Name,
					"pvc", vol.PvcRef.Name,
					"namespace", vol.PvcRef.Namespace)
				continue
			}
			totalUsedBytes += *vol.UsedBytes
		}
		return totalUsedBytes, nil
	}
	return 0, fmt.Errorf("pod %s/%s not found in kubelet summary", namespace, podName)
}
