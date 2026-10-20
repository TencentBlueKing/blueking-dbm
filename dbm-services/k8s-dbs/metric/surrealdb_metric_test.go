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

// TestSurrealDBGetStorageUsage_NilK8sClient 验证 K8sClient 为 nil 时返回明确错误
func TestSurrealDBGetStorageUsage_NilK8sClient(t *testing.T) {
	fetcher := NewSurrealDBClusterMetricFetcher()
	params := &ClusterMetricQueryParams{
		AddonType: "surrealdb",
		Namespace: "surrealdb-ns",
		PodName:   "surreal-tikv-0",
		K8sClient: nil,
	}

	_, err := fetcher.GetStorageUsage(params)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "K8sClient")
}
