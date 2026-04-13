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
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestExtractPodVolumeUsedBytes_Found 验证多个 PVC 的用量被正确累加
func TestExtractPodVolumeUsedBytes_Found(t *testing.T) {
	val1 := uint64(1073741824) // 1 GiB
	val2 := uint64(536870912)  // 0.5 GiB
	summary := &kubeletSummary{
		Pods: []kubeletPodStats{
			{
				PodRef: kubeletPodRef{Name: "qdrant-0", Namespace: "qdrant-ns"},
				Volumes: []kubeletVolumeStats{
					{Name: "data", UsedBytes: &val1},
					{Name: "snapshots", UsedBytes: &val2},
				},
			},
		},
	}

	usedBytes, err := extractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(1610612736), usedBytes) // 1.5 GiB
}

// TestExtractPodVolumeUsedBytes_NilUsedBytes 验证 usedBytes 为 nil 时安全跳过
func TestExtractPodVolumeUsedBytes_NilUsedBytes(t *testing.T) {
	val := uint64(2147483648) // 2 GiB
	summary := &kubeletSummary{
		Pods: []kubeletPodStats{
			{
				PodRef: kubeletPodRef{Name: "qdrant-0", Namespace: "qdrant-ns"},
				Volumes: []kubeletVolumeStats{
					{Name: "data", UsedBytes: &val},
					{Name: "tmp", UsedBytes: nil}, // 暂不可用，应安全跳过
				},
			},
		},
	}

	usedBytes, err := extractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(2147483648), usedBytes)
}

// TestExtractPodVolumeUsedBytes_AllNilUsedBytes 验证所有 usedBytes 为 nil 时返回 0
func TestExtractPodVolumeUsedBytes_AllNilUsedBytes(t *testing.T) {
	summary := &kubeletSummary{
		Pods: []kubeletPodStats{
			{
				PodRef: kubeletPodRef{Name: "qdrant-0", Namespace: "qdrant-ns"},
				Volumes: []kubeletVolumeStats{
					{Name: "data", UsedBytes: nil},
					{Name: "tmp", UsedBytes: nil},
				},
			},
		},
	}

	usedBytes, err := extractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(0), usedBytes)
}

// TestExtractPodVolumeUsedBytes_NoVolumes 验证 Pod 无 volume 时返回 0
func TestExtractPodVolumeUsedBytes_NoVolumes(t *testing.T) {
	summary := &kubeletSummary{
		Pods: []kubeletPodStats{
			{
				PodRef:  kubeletPodRef{Name: "qdrant-0", Namespace: "qdrant-ns"},
				Volumes: []kubeletVolumeStats{},
			},
		},
	}

	usedBytes, err := extractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(0), usedBytes)
}

// TestExtractPodVolumeUsedBytes_NotFound 验证 Pod 不存在时返回明确错误
func TestExtractPodVolumeUsedBytes_NotFound(t *testing.T) {
	summary := &kubeletSummary{
		Pods: []kubeletPodStats{
			{
				PodRef: kubeletPodRef{Name: "other-pod", Namespace: "other-ns"},
				Volumes: []kubeletVolumeStats{
					{Name: "data", UsedBytes: func() *uint64 { v := uint64(1024); return &v }()},
				},
			},
		},
	}

	_, err := extractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "qdrant-ns/qdrant-0")
}

// TestExtractPodVolumeUsedBytes_NamespaceMismatch 验证 namespace 不匹配时不错误地匹配同名 Pod
func TestExtractPodVolumeUsedBytes_NamespaceMismatch(t *testing.T) {
	val := uint64(1024)
	summary := &kubeletSummary{
		Pods: []kubeletPodStats{
			{
				PodRef: kubeletPodRef{Name: "qdrant-0", Namespace: "wrong-ns"},
				Volumes: []kubeletVolumeStats{
					{Name: "data", UsedBytes: &val},
				},
			},
		},
	}

	_, err := extractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.Error(t, err)
}

// TestGetStorageUsage_NilK8sClient 验证 K8sClient 为 nil 时返回明确错误
func TestGetStorageUsage_NilK8sClient(t *testing.T) {
	fetcher := NewQdrantClusterMetricFetcher()
	params := &ClusterMetricQueryParams{
		AddonType: "qdrant",
		Namespace: "qdrant-ns",
		PodName:   "qdrant-0",
		K8sClient: nil,
	}

	_, err := fetcher.GetStorageUsage(params)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "K8sClient")
}

// TestQdrantGetStorageUsage 集成测试：需要真实 K8s 集群环境
// 运行方式：配置真实 K8s 集群后执行
// go test ./metric/... -run TestQdrantGetStorageUsage -v
//
//nolint:unused
func _TestQdrantGetStorageUsage(t *testing.T) {
	// 集成测试占位，需要真实集群配置
	// 参考 vm_metric_test.go 模式，通过 K8sClusterConfigEntity 构造 K8sClient
	t.Skip("integration test: requires real K8s cluster")
}
