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

// TestQdrantGetStorageUsage_NilK8sClient 验证 K8sClient 为 nil 时返回明确错误
func TestQdrantGetStorageUsage_NilK8sClient(t *testing.T) {
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
