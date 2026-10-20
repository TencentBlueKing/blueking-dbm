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

package util

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// pvcRef 测试辅助：构造一个 PVC 引用
func pvcRef(name, namespace string) *KubeletPVCRef {
	return &KubeletPVCRef{Name: name, Namespace: namespace}
}

// TestExtractPodVolumeUsedBytes_Found 验证多个 PVC 的用量被正确累加
func TestExtractPodVolumeUsedBytes_Found(t *testing.T) {
	val1 := uint64(1073741824) // 1 GiB
	val2 := uint64(536870912)  // 0.5 GiB
	summary := &KubeletSummary{
		Pods: []KubeletPodStats{
			{
				PodRef: KubeletPodRef{Name: "qdrant-0", Namespace: "qdrant-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "data", UsedBytes: &val1, PvcRef: pvcRef("data-qdrant-0", "qdrant-ns")},
					{Name: "snapshots", UsedBytes: &val2, PvcRef: pvcRef("snapshots-qdrant-0", "qdrant-ns")},
				},
			},
		},
	}

	usedBytes, err := ExtractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(1610612736), usedBytes) // 1.5 GiB
}

// TestExtractPodVolumeUsedBytes_SkipNonPVC 验证 configmap/token/emptyDir 等
// 非 PVC volume 不会被累加，避免干扰 PVC 使用量统计
func TestExtractPodVolumeUsedBytes_SkipNonPVC(t *testing.T) {
	dataUsed := uint64(1073741824) // 1 GiB - PVC
	tokenUsed := uint64(4096)      // 4 KiB - projected token，不应被累加
	configUsed := uint64(12288)    // 12 KiB - configMap，不应被累加
	tmpUsed := uint64(104857600)   // 100 MiB - emptyDir，不应被累加

	summary := &KubeletSummary{
		Pods: []KubeletPodStats{
			{
				PodRef: KubeletPodRef{Name: "qdrant-0", Namespace: "qdrant-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "data", UsedBytes: &dataUsed, PvcRef: pvcRef("data-qdrant-0", "qdrant-ns")},
					{Name: "kube-api-access-xxxxx", UsedBytes: &tokenUsed}, // 无 PvcRef
					{Name: "config", UsedBytes: &configUsed},               // 无 PvcRef
					{Name: "tmp-cache", UsedBytes: &tmpUsed},               // 无 PvcRef
				},
			},
		},
	}

	usedBytes, err := ExtractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(1073741824), usedBytes) // 仅 PVC 的 1 GiB
}

// TestExtractPodVolumeUsedBytes_NilUsedBytes 验证 PVC 的 usedBytes 为 nil 时安全跳过
func TestExtractPodVolumeUsedBytes_NilUsedBytes(t *testing.T) {
	val := uint64(2147483648) // 2 GiB
	summary := &KubeletSummary{
		Pods: []KubeletPodStats{
			{
				PodRef: KubeletPodRef{Name: "qdrant-0", Namespace: "qdrant-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "data", UsedBytes: &val, PvcRef: pvcRef("data-qdrant-0", "qdrant-ns")},
					// 第二个 PVC usedBytes 不可用（Block 模式 PVC 或暂未采集），应安全跳过
					{Name: "wal", UsedBytes: nil, PvcRef: pvcRef("wal-qdrant-0", "qdrant-ns")},
				},
			},
		},
	}

	usedBytes, err := ExtractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(2147483648), usedBytes)
}

// TestExtractPodVolumeUsedBytes_AllNilUsedBytes 验证所有 PVC usedBytes 为 nil 时返回 0
func TestExtractPodVolumeUsedBytes_AllNilUsedBytes(t *testing.T) {
	summary := &KubeletSummary{
		Pods: []KubeletPodStats{
			{
				PodRef: KubeletPodRef{Name: "qdrant-0", Namespace: "qdrant-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "data", UsedBytes: nil, PvcRef: pvcRef("data-qdrant-0", "qdrant-ns")},
					{Name: "wal", UsedBytes: nil, PvcRef: pvcRef("wal-qdrant-0", "qdrant-ns")},
				},
			},
		},
	}

	usedBytes, err := ExtractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(0), usedBytes)
}

// TestExtractPodVolumeUsedBytes_NoVolumes 验证 Pod 无 volume 时返回 0
func TestExtractPodVolumeUsedBytes_NoVolumes(t *testing.T) {
	summary := &KubeletSummary{
		Pods: []KubeletPodStats{
			{
				PodRef:  KubeletPodRef{Name: "qdrant-0", Namespace: "qdrant-ns"},
				Volumes: []KubeletVolumeStats{},
			},
		},
	}

	usedBytes, err := ExtractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(0), usedBytes)
}

// TestExtractPodVolumeUsedBytes_OnlyNonPVC 验证 Pod 仅挂载非 PVC volume 时返回 0
func TestExtractPodVolumeUsedBytes_OnlyNonPVC(t *testing.T) {
	tokenUsed := uint64(4096)
	configUsed := uint64(12288)
	summary := &KubeletSummary{
		Pods: []KubeletPodStats{
			{
				PodRef: KubeletPodRef{Name: "nopvc-pod", Namespace: "qdrant-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "kube-api-access-xxxxx", UsedBytes: &tokenUsed},
					{Name: "config", UsedBytes: &configUsed},
				},
			},
		},
	}

	usedBytes, err := ExtractPodVolumeUsedBytes(summary, "qdrant-ns", "nopvc-pod")
	require.NoError(t, err)
	assert.Equal(t, uint64(0), usedBytes)
}

// TestExtractPodVolumeUsedBytes_NotFound 验证 Pod 不存在时返回明确错误
func TestExtractPodVolumeUsedBytes_NotFound(t *testing.T) {
	val := uint64(1024)
	summary := &KubeletSummary{
		Pods: []KubeletPodStats{
			{
				PodRef: KubeletPodRef{Name: "other-pod", Namespace: "other-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "data", UsedBytes: &val, PvcRef: pvcRef("data-other-pod", "other-ns")},
				},
			},
		},
	}

	_, err := ExtractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.Error(t, err)
	assert.Contains(t, err.Error(), "qdrant-ns/qdrant-0")
}

// TestExtractPodVolumeUsedBytes_NamespaceMismatch 验证 namespace 不匹配时不错误地匹配同名 Pod
func TestExtractPodVolumeUsedBytes_NamespaceMismatch(t *testing.T) {
	val := uint64(1024)
	summary := &KubeletSummary{
		Pods: []KubeletPodStats{
			{
				PodRef: KubeletPodRef{Name: "qdrant-0", Namespace: "wrong-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "data", UsedBytes: &val, PvcRef: pvcRef("data-qdrant-0", "wrong-ns")},
				},
			},
		},
	}

	_, err := ExtractPodVolumeUsedBytes(summary, "qdrant-ns", "qdrant-0")
	require.Error(t, err)
}

// TestExtractPodVolumeUsedBytes_MultiPod 验证 SurrealDB 多组件（tikv/pd/surreal）
// 的 Pod volume 用量可被独立正确提取
func TestExtractPodVolumeUsedBytes_MultiPod(t *testing.T) {
	tikvUsed := uint64(2147483648)   // 2 GiB
	pdUsed := uint64(1073741824)     // 1 GiB
	surrealUsed := uint64(536870912) // 0.5 GiB

	summary := &KubeletSummary{
		Pods: []KubeletPodStats{
			{
				PodRef: KubeletPodRef{Name: "surreal-tikv-0", Namespace: "surrealdb-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "data", UsedBytes: &tikvUsed, PvcRef: pvcRef("tikv-surreal-tikv-0", "surrealdb-ns")},
				},
			},
			{
				PodRef: KubeletPodRef{Name: "surreal-pd-0", Namespace: "surrealdb-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "data", UsedBytes: &pdUsed, PvcRef: pvcRef("pd-surreal-pd-0", "surrealdb-ns")},
				},
			},
			{
				PodRef: KubeletPodRef{Name: "surreal-surreal-0", Namespace: "surrealdb-ns"},
				Volumes: []KubeletVolumeStats{
					{Name: "data", UsedBytes: &surrealUsed, PvcRef: pvcRef("surreal-surreal-surreal-0", "surrealdb-ns")},
				},
			},
		},
	}

	tikvBytes, err := ExtractPodVolumeUsedBytes(summary, "surrealdb-ns", "surreal-tikv-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(2147483648), tikvBytes)

	pdBytes, err := ExtractPodVolumeUsedBytes(summary, "surrealdb-ns", "surreal-pd-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(1073741824), pdBytes)

	surrealBytes, err := ExtractPodVolumeUsedBytes(summary, "surrealdb-ns", "surreal-surreal-0")
	require.NoError(t, err)
	assert.Equal(t, uint64(536870912), surrealBytes)
}
