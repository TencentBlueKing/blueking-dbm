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

package provider

import (
	"fmt"
	coreclient "k8s-dbs/core/client"
	clientconst "k8s-dbs/core/client/constants"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"slices"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

// ComponentProvider 组件管理核心服务
type ComponentProvider struct {
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
}

// DescribeComponent 获取组件详情
func (c *ComponentProvider) DescribeComponent(request *coreentity.Request) (*coreentity.ComponentDetail, error) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	crd := &coreentity.CustomResourceDefinition{
		GroupVersionResource: kbtypes.PodGVR(),
		Namespace:            request.Namespace,
		Labels: map[string]string{
			coreconst.InstanceName:  request.ClusterName,
			coreconst.ComponentName: request.ComponentName,
		},
	}
	podList, err := coreclient.ListCRD(k8sClient, crd)
	if err != nil {
		return nil, err
	}

	if podList.Items != nil && len(podList.Items) == 0 {
		return nil, fmt.Errorf("the pod of the component %s currently being queried is empty", request.ComponentName)
	}

	var pods []coreentity.Pod
	var env []corev1.EnvVar
	for _, item := range podList.Items {
		// Try converting Unstructured to Pod type
		pod := &corev1.Pod{}
		err := runtime.DefaultUnstructuredConverter.FromUnstructured(item.Object, pod)
		if err != nil {
			return nil, fmt.Errorf("cannot be converted to Pod format, raw data will be displayed: %v", err)
		}
		var role string
		if podRole, exits := pod.Labels["kubeblocks.io/role"]; exits {
			role = podRole
		}
		pods = append(pods, coreentity.Pod{
			PodName:     pod.Name,
			Status:      pod.Status.Phase,
			Node:        pod.Spec.NodeName,
			Role:        role,
			CreatedTime: pod.CreationTimestamp.String(),
		})
		if env == nil {
			env = pod.Spec.Containers[0].Env
		}

	}

	// Remove kb specific environment variables
	env = slices.DeleteFunc(env, func(envVar corev1.EnvVar) bool {
		_, exists := clientconst.KbEnvVar[envVar.Name]
		return exists
	})

	componentDetail := &coreentity.ComponentDetail{
		Metadata: coreentity.Metadata{
			ClusterName:   crd.Labels[coreconst.InstanceName],
			Namespace:     crd.Namespace,
			ComponentName: crd.Labels[coreconst.ComponentName],
		},
		Pods: pods,
		Env:  env,
	}

	return componentDetail, nil
}

// NewComponentProvider 创建 ComponentProvider 实例
func NewComponentProvider(
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
) *ComponentProvider {
	return &ComponentProvider{
		clusterConfigProvider,
	}
}
