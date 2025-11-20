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

package constant

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestGetAPIGroup 测试获取 APIGroup
func TestGetAPIGroup(t *testing.T) {
	apiName := "v4_dbs_cluster_vscaling"
	actual := GetAPIGroup(apiName)
	assert.Equal(t, APIGroupCluster, actual)

	apiName = "v4_dbs_addon_install"
	actual = GetAPIGroup(apiName)
	assert.Equal(t, APIGroupAddon, actual)

	apiName = "test_api"
	actual = GetAPIGroup(apiName)
	assert.Equal(t, APIGroupUnknown, actual)
}
