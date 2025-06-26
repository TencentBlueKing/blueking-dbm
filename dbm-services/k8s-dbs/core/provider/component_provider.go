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
	"context"
	"fmt"
	coreclient "k8s-dbs/core/client"
	clientconst "k8s-dbs/core/client/constants"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	pventity "k8s-dbs/core/provider/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"
	"slices"
	"strings"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	"github.com/google/go-cmp/cmp"
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

// GetComponentInternalSvc 获取组件的内部服务链接
func (c *ComponentProvider) GetComponentInternalSvc(svcEntity *pventity.K8sSvcEntity) (
	[]coreentity.K8sInternalSvcInfo,
	error,
) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(svcEntity.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}
	namespace := svcEntity.Namespace
	labelSelector := mapToLabelSelector(map[string]string{
		coreconst.InstanceName:  svcEntity.ClusterName,
		coreconst.ComponentName: svcEntity.ComponentName,
		coreconst.ManagedBy:     coreconst.Kubeblocks,
	})
	labelSelector += ",dbs_k8s_service_type!=LoadBalancer"
	clusterIPServices, err := k8sClient.ClientSet.CoreV1().Services(namespace).
		List(context.TODO(), metav1.ListOptions{
			LabelSelector: labelSelector,
		})
	if err != nil {
		slog.Error("failed to list k8s services",
			"namespace", namespace, "labelSelector", labelSelector, "err", err.Error())
		return nil, err
	}
	if clusterIPServices == nil {
		slog.Warn("clusterIPServices is empty",
			"namespace", namespace, "labelSelector", labelSelector)
		return []coreentity.K8sInternalSvcInfo{}, nil
	}
	k8sSvcInfos := c.convertInternalSvc(clusterIPServices)
	return k8sSvcInfos, nil
}

// GetComponentExternalSvc 获取组件的外部服务链接
func (c *ComponentProvider) GetComponentExternalSvc(svcEntity *pventity.K8sSvcEntity) (
	[]coreentity.K8sExternalSvcInfo,
	error,
) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(svcEntity.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}
	namespace := svcEntity.Namespace
	labelSelector := mapToLabelSelector(map[string]string{
		coreconst.InstanceName: svcEntity.ClusterName,
		coreconst.ManagedBy:    coreconst.Kubeblocks,
	})

	lbServices, err := k8sClient.ClientSet.CoreV1().Services(namespace).
		List(context.TODO(), metav1.ListOptions{
			LabelSelector: labelSelector,
		})
	if err != nil {
		slog.Error("failed to list k8s services",
			"namespace", namespace, "labelSelector", labelSelector, "err", err.Error())
		return nil, err
	}
	if lbServices == nil {
		slog.Warn("lbServices is empty",
			"namespace", namespace, "labelSelector", labelSelector)
		return []coreentity.K8sExternalSvcInfo{}, nil
	}
	svcSelector := map[string]string{
		coreconst.InstanceName:  svcEntity.ClusterName,
		coreconst.ManagedBy:     coreconst.Kubeblocks,
		coreconst.ComponentName: svcEntity.ComponentName,
	}
	k8sSvcInfos := c.convertExternalSvc(lbServices, svcSelector)
	return k8sSvcInfos, nil
}

// mapToLabelSelector 将 map[string]string 转换为 Label Selector 字符串
func mapToLabelSelector(labels map[string]string) string {
	var selectorParts []string
	for key, value := range labels {
		selectorParts = append(selectorParts, fmt.Sprintf("%s=%s", key, value))
	}
	return strings.Join(selectorParts, ",")
}

// convertInternalSvc 转换 clusterIP 为 K8sInternalSvcInfo
func (c *ComponentProvider) convertInternalSvc(clusterIPServices *corev1.ServiceList) []coreentity.K8sInternalSvcInfo {
	var k8sSvcInfos []coreentity.K8sInternalSvcInfo
	for _, service := range clusterIPServices.Items {
		fqdn := fmt.Sprintf("%s.%s.svc.cluster.local", service.Namespace, service.Namespace)
		var ports []coreentity.PortInfo
		for _, port := range service.Spec.Ports {
			fullAddr := fmt.Sprintf("%s:%d", fqdn, port.Port)
			ports = append(ports, coreentity.PortInfo{
				Port:     port.Port,
				Protocol: string(port.Protocol),
				FullAddr: fullAddr,
			})
		}
		k8sSvcInfos = append(k8sSvcInfos, coreentity.K8sInternalSvcInfo{
			Name:      service.Name,
			Namespace: service.Namespace,
			FQDN:      fqdn,
			Ports:     ports,
		})
	}
	return k8sSvcInfos
}

// convertInternalSvc 转换 LoadBalancer 为 K8sExternalSvcInfo
func (c *ComponentProvider) convertExternalSvc(
	lbServices *corev1.ServiceList,
	svcSelector map[string]string,
) []coreentity.K8sExternalSvcInfo {
	var k8sSvcInfos []coreentity.K8sExternalSvcInfo
	for _, service := range lbServices.Items {
		if !cmp.Equal(service.Spec.Selector, svcSelector) {
			continue
		}
		if len(service.Status.LoadBalancer.Ingress) == 0 {
			slog.Warn("service LoadBalancer Ingress is empty",
				"serviceName", service.Name, "namespace", service.Namespace)
			continue
		}
		ingress := service.Status.LoadBalancer.Ingress[0]
		var externalPorts []coreentity.ExternalPort
		for _, port := range service.Spec.Ports {
			fullAddr := fmt.Sprintf("%s:%d", ingress.IP, port.Port)
			externalPorts = append(externalPorts, coreentity.ExternalPort{
				Port:     port.Port,
				Protocol: string(port.Protocol),
				FullAddr: fullAddr,
			})
		}
		k8sSvcInfos = append(k8sSvcInfos, coreentity.K8sExternalSvcInfo{
			Name:      service.Name,
			Namespace: service.Namespace,
			Hostname:  ingress.IP,
			Ports:     externalPorts,
		})
	}
	return k8sSvcInfos
}

// NewComponentProvider 创建 ComponentProvider 实例
func NewComponentProvider(
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
) *ComponentProvider {
	return &ComponentProvider{
		clusterConfigProvider,
	}
}
