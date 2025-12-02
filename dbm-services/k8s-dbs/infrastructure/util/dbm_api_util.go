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
	"fmt"
	coreconst "k8s-dbs/core/constant"
)

// clusterTypeMap 存储插件类型到DBM集群类型的映射表
var clusterTypeMap = map[string]string{
	string(coreconst.Victoriametrics): "k8s_vm",
	string(coreconst.Greptimedb):      "k8s_gt",
	string(coreconst.Surreal):         "k8s_surreal",
	string(coreconst.Risingwave):      "k8s_rw",
	string(coreconst.Milvus):          "k8s_mv",
}

// GetDbmClusterType 获取对应的 dbm cluster type
func GetDbmClusterType(storageAddonType string) (string, error) {
	if clusterType, exists := clusterTypeMap[storageAddonType]; exists {
		return clusterType, nil
	}

	return "", fmt.Errorf("不支持的存储插件类型: %s", storageAddonType)
}
