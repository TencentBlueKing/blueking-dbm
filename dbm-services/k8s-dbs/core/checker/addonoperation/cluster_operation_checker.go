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

package addonoperation

import coreentity "k8s-dbs/core/entity"

var ClusterOpsChecker = &ClusterOperationChecker{
	rules: make(map[AddonType]map[OperationType]OperationCheckFunc),
}

// ClusterOperationChecker 集群行为检查器
type ClusterOperationChecker struct {
	rules map[AddonType]map[OperationType]OperationCheckFunc
}

// Register 为某个存储系统下的某个组件 + 操作注册检查函数
func (c *ClusterOperationChecker) Register(
	addonType AddonType,
	operation OperationType,
	checker OperationCheckFunc,

) {
	if _, ok := c.rules[addonType]; !ok {
		c.rules[addonType] = make(map[OperationType]OperationCheckFunc)
	}
	c.rules[addonType][operation] = checker
}

// Check 执行检查
func (c *ClusterOperationChecker) Check(
	addonType AddonType,
	operation OperationType,
	request *coreentity.Request,
) (bool, error) {
	storageRules, ok := c.rules[addonType]
	if !ok {
		// 该存储系统没有注册任何规则，默认允许
		return true, nil
	}

	checker, ok := storageRules[operation]
	if !ok {
		// 该操作没有注册规则，默认允许
		return true, nil
	}

	// 执行检查函数
	return checker(operation, request)
}
