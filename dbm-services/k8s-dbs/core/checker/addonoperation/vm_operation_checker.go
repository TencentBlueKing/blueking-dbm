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
	commentity "k8s-dbs/common/entity"
	coreentity "k8s-dbs/core/entity"
	"k8s-dbs/errors"
)

// VMStorageVExpansionCheck vmstorage 组件磁盘扩缩容检查
func VMStorageVExpansionCheck(
	_ *commentity.DbsContext,
	operationType OperationType,
	request *coreentity.Request,
) (bool, error) {
	if operationType != VExpansion {
		return false, errors.NewK8sDbsError(errors.ParameterInvalidError,
			fmt.Errorf("操作类型错误，不属于磁盘扩缩容。操作类型:%s", operationType))
	}
	for _, component := range request.ComponentList {
		componentName := component.ComponentName
		if componentName == string(ComponentVMStorage) {
			storageSize := component.Storage
			if storageSize.Value() < 0 {
				return false, errors.NewK8sDbsError(errors.OperationForbidden, fmt.Errorf("vmstorage 节点禁止执行磁盘缩容操作"))
			}
		}
	}
	return true, nil
}

// VMStorageHScaleCheck vmstorage 组件水平扩缩容检查
func VMStorageHScaleCheck(
	_ *commentity.DbsContext,
	operationType OperationType,
	request *coreentity.Request,
) (bool, error) {
	if operationType != HScaling {
		return false, errors.NewK8sDbsError(errors.ParameterInvalidError,
			fmt.Errorf("操作类型错误，不属于水平扩缩容。操作类型:%s", operationType))
	}
	for _, hScale := range request.HorizontalScalingList {
		componentName := hScale.ComponentName
		if componentName == string(ComponentVMStorage) {
			if hScale.ScaleIn != nil {
				return false, errors.NewK8sDbsError(errors.OperationForbidden,
					fmt.Errorf("vmstorage 组件禁止执行水平缩容操作"))
			}
		}
	}
	return true, nil
}

func init() {
	ComponentOpsChecker.Register(AddonVM, ComponentVMStorage, HScaling, VMStorageHScaleCheck)
	ComponentOpsChecker.Register(AddonVM, ComponentVMStorage, VExpansion, VMStorageVExpansionCheck)
	ClusterOpsChecker.Register(AddonVM, DeleteCluster, ClusterDeleteCheck)
}
