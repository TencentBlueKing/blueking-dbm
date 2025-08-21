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
	commutil "k8s-dbs/common/util"

	"helm.sh/helm/v3/pkg/action"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// UninstallClusterRelease 卸载 cluster release
func UninstallClusterRelease(
	k8sClient *commutil.K8sClient,
	namespace string,
	clusterName string,
	deletePropagation metav1.DeletionPropagation) error {
	// init helm client
	actionConfig, err := k8sClient.BuildHelmConfig(namespace)
	if err != nil {
		return err
	}
	uninstall := action.NewUninstall(actionConfig)
	uninstall.DeletionPropagation = string(deletePropagation)
	_, err = uninstall.Run(clusterName)
	if err != nil {
		return err
	}
	return nil
}

// CheckClusterReleaseExists 检查指定 ns 下 release 是否存在
func CheckClusterReleaseExists(k8sClient *commutil.K8sClient, namespace string, clusterName string) (bool, error) {
	actionConfig, err := k8sClient.BuildHelmConfig(namespace)
	if err != nil {
		return false, fmt.Errorf("failed to build helm config: %v", err)
	}
	get := action.NewGet(actionConfig)
	_, err = get.Run(clusterName)
	if err != nil {
		return false, fmt.Errorf("failed to get helm release: %v", err)
	}
	return true, nil
}
