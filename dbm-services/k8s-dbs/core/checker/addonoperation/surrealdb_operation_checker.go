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

import (
	"fmt"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/errors"
)

// SurrealTikvVExpansionCheck surreal tikv 组件磁盘扩缩容检查
func SurrealTikvVExpansionCheck(operationType OperationType, request *coreentity.Request) (bool, error) {
	if operationType != VExpansion {
		return false, errors.NewK8sDbsError(errors.ParameterInvalidError,
			fmt.Errorf("操作类型错误，不属于磁盘扩缩容。操作类型:%s", operationType))
	}
	for _, component := range request.ComponentList {
		componentName := component.ComponentName
		if componentName == string(ComponentSurrealTikv) {
			storageSize := component.Storage
			if storageSize.Value() < 0 {
				return false, errors.NewK8sDbsError(errors.OperationFobidden,
					fmt.Errorf("surreal tikv 节点禁止执行磁盘缩容操作"))
			}
		}
	}
	return true, nil
}

// SurrealTikvHScaleCheck surreal tikv 组件水平扩缩容检查
func SurrealTikvHScaleCheck(operationType OperationType, request *coreentity.Request) (bool, error) {
	if operationType != HScaling {
		return false, errors.NewK8sDbsError(errors.ParameterInvalidError,
			fmt.Errorf("操作类型错误，不属于水平扩缩容。操作类型:%s", operationType))
	}
	for _, hScale := range request.HorizontalScalingList {
		componentName := hScale.ComponentName
		if componentName == string(ComponentSurrealTikv) {
			if hScale.ScaleIn != nil {
				return false, errors.NewK8sDbsError(errors.OperationFobidden,
					fmt.Errorf("surreal tikv 组件禁止执行水平缩容操作"))
			}
		}
	}
	return true, nil
}

// SurrealPdVExpansionCheck surreal pd 组件磁盘扩缩容检查
func SurrealPdVExpansionCheck(operationType OperationType, request *coreentity.Request) (bool, error) {
	if operationType != VExpansion {
		return false, errors.NewK8sDbsError(errors.ParameterInvalidError,
			fmt.Errorf("操作类型错误，不属于磁盘扩缩容。操作类型:%s", operationType))
	}
	for _, component := range request.ComponentList {
		componentName := component.ComponentName
		if componentName == string(ComponentSurrealPd) {
			storageSize := component.Storage
			if storageSize.Value() < 0 {
				return false, errors.NewK8sDbsError(errors.OperationFobidden,
					fmt.Errorf("surreal pd 节点禁止执行磁盘缩容操作"))
			}
		}
	}
	return true, nil
}

// SurrealPdHScaleCheck surreal pd 组件水平扩缩容检查
func SurrealPdHScaleCheck(operationType OperationType, request *coreentity.Request) (bool, error) {
	if operationType != HScaling {
		return false, errors.NewK8sDbsError(errors.ParameterInvalidError,
			fmt.Errorf("操作类型错误，不属于水平扩缩容。操作类型:%s", operationType))
	}
	for _, hScale := range request.HorizontalScalingList {
		componentName := hScale.ComponentName
		if componentName == string(ComponentSurrealPd) {
			if hScale.ScaleIn != nil {
				return false, errors.NewK8sDbsError(errors.OperationFobidden,
					fmt.Errorf("surreal pd 组件禁止执行水平缩容操作"))
			}
		}
	}
	return true, nil
}

func init() {
	ComponentOpsChecker.Register(AddonSurrealDB, ComponentSurrealTikv, VExpansion, SurrealTikvVExpansionCheck)
	ComponentOpsChecker.Register(AddonSurrealDB, ComponentSurrealTikv, HScaling, SurrealTikvHScaleCheck)
	ComponentOpsChecker.Register(AddonSurrealDB, ComponentSurrealPd, VExpansion, SurrealPdVExpansionCheck)
	ComponentOpsChecker.Register(AddonSurrealDB, ComponentSurrealPd, HScaling, SurrealPdHScaleCheck)
}
