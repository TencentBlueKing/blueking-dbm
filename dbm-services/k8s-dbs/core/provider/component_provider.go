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
	commentity "k8s-dbs/common/entity"
	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	coreutil "k8s-dbs/core/util"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"
	"slices"
	"strings"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"

	"github.com/google/go-cmp/cmp"
	corev1 "k8s.io/api/core/v1"
)

// ComponentProvider 组件管理核心服务
type ComponentProvider struct {
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
	clusterMetaProvider   metaprovider.K8sCrdClusterProvider
}

// DescribeComponent 获取组件详情
func (c *ComponentProvider) DescribeComponent(request *coreentity.Request) (*coreentity.ComponentDetail, error) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
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

	podList, err := coreutil.ListCRD(k8sClient, crd)
	if err != nil {
		return nil, fmt.Errorf("failed to list pods for component %s: %w", request.ComponentName, err)
	}
	if len(podList.Items) == 0 {
		return nil, fmt.Errorf("no pods found for component %s in namespace %s", request.ComponentName, request.Namespace)
	}
	var clusterMetaParams = &metaentity.ClusterQueryParams{
		K8sClusterConfigID: k8sClusterConfig.ID,
		Namespace:          request.Namespace,
		ClusterName:        request.ClusterName,
	}
	clusterMeta, err := c.clusterMetaProvider.FindByParams(clusterMetaParams)
	if err != nil {
		return nil, err
	}

	pods, err := coreutil.ExtractPodsInfo(clusterMeta.AddonInfo.AddonType, k8sClusterConfig.ClusterName,
		k8sClient, podList)
	if err != nil {
		return nil, fmt.Errorf("failed to extract pod details: %w", err)
	}

	envVars, err := extractEnvVars(podList)
	if err != nil {
		return nil, fmt.Errorf("failed to extract env vars: %w", err)
	}
	envVars = filterOutKbEnvVars(envVars)
	componentDetail := &coreentity.ComponentDetail{
		Metadata: coreentity.Metadata{
			ClusterName:   crd.Labels[coreconst.InstanceName],
			Namespace:     crd.Namespace,
			ComponentName: crd.Labels[coreconst.ComponentName],
		},
		Pods: pods,
		Env:  envVars,
	}
	return componentDetail, nil
}

// extractEnvVars 从 Pod 列表中提取环境变量（仅取第一个容器的 Env）
func extractEnvVars(podList *unstructured.UnstructuredList) ([]corev1.EnvVar, error) {
	if len(podList.Items) == 0 {
		return nil, fmt.Errorf("pod list is empty")
	}
	// 只取第一个 Pod 的第一个容器的 Env（根据你的业务逻辑调整）
	firstPod := podList.Items[0]
	pod, err := coreutil.ConvertUnstructuredToPod(firstPod)
	if err != nil {
		return nil, fmt.Errorf("failed to convert unstructured pod %s: %w", firstPod.GetName(), err)
	}

	if len(pod.Spec.Containers) == 0 {
		return nil, fmt.Errorf("pod %s has no containers", pod.Name)
	}
	return pod.Spec.Containers[0].Env, nil
}

// filterOutKbEnvVars 过滤掉 KB 特定的环境变量
func filterOutKbEnvVars(envVars []corev1.EnvVar) []corev1.EnvVar {
	return slices.DeleteFunc(envVars, func(envVar corev1.EnvVar) bool {
		_, exists := coreconst.KbEnvVar[envVar.Name]
		return exists
	})
}

// GetComponentInternalSvc 获取组件的内部服务链接
func (c *ComponentProvider) GetComponentInternalSvc(svcEntity *coreentity.K8sSvcEntity) (
	[]coreentity.K8sInternalSvcInfo,
	error,
) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(svcEntity.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
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
func (c *ComponentProvider) GetComponentExternalSvc(svcEntity *coreentity.K8sSvcEntity) (
	[]coreentity.K8sExternalSvcInfo,
	error,
) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(svcEntity.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)

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
		fqdn := fmt.Sprintf("%s.%s.svc.cluster.local", service.Name, service.Namespace)
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

// ListPods 获取实例列表
func (c *ComponentProvider) ListPods(
	params *coreentity.ComponentQueryParams,
	pagination *commentity.Pagination,
) ([]*coreentity.Pod, uint64, error) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(params.K8sClusterName)
	if err != nil {
		return nil, 0, err
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, 0, err
	}
	var clusterMetaParams = &metaentity.ClusterQueryParams{
		K8sClusterConfigID: k8sClusterConfig.ID,
		Namespace:          params.Namespace,
		ClusterName:        params.ClusterName,
	}
	clusterMeta, err := c.clusterMetaProvider.FindByParams(clusterMetaParams)
	if err != nil {
		return nil, 0, err
	}
	pods, err := coreutil.GetComponentPods(clusterMeta.AddonInfo.AddonType, params, k8sClient)
	if err != nil {
		return nil, 0, err
	}
	count := uint64(len(pods))
	if pagination == nil {
		return pods, count, nil
	}
	pods, err = commutil.Paginate(pagination, pods)
	if err != nil {
		return nil, 0, err
	}
	return pods, count, nil

}

// NewComponentProvider 创建 ComponentProvider 实例
func NewComponentProvider(
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
) *ComponentProvider {
	return &ComponentProvider{
		clusterConfigProvider,
		clusterMetaProvider,
	}
}
