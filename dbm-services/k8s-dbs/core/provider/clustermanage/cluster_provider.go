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

package clustermanage

import (
	"context"
	"fmt"
	coreclient "k8s-dbs/core/client"
	clientconst "k8s-dbs/core/client/constants"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	metaprovider "k8s-dbs/metadata/provider"
	providerentity "k8s-dbs/metadata/provider/entity"
	"slices"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

// ClusterProvider 集群管理核心服务
type ClusterProvider struct {
	clusterMetaProvider          metaprovider.K8sCrdClusterProvider
	componentMetaProvider        metaprovider.K8sCrdComponentProvider
	cdMetaProvider               metaprovider.K8sCrdClusterDefinitionProvider
	cmpdMetaProvider             metaprovider.K8sCrdCmpdProvider
	cmpvMetaProvider             metaprovider.K8sCrdCmpvProvider
	k8sClusterConfigMetaProvider metaprovider.K8sClusterConfigProvider
}

// NewClusterService 创建 ClusterProvider 实例
func NewClusterService(
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	componentMetaProvider metaprovider.K8sCrdComponentProvider,
	cdMetaProvider metaprovider.K8sCrdClusterDefinitionProvider,
	cmpdMetaProvider metaprovider.K8sCrdCmpdProvider,
	cmpvMetaProvider metaprovider.K8sCrdCmpvProvider,
	k8sClusterConfigMetaProvider metaprovider.K8sClusterConfigProvider,
) *ClusterProvider {
	return &ClusterProvider{
		clusterMetaProvider:          clusterMetaProvider,
		componentMetaProvider:        componentMetaProvider,
		cdMetaProvider:               cdMetaProvider,
		cmpdMetaProvider:             cmpdMetaProvider,
		cmpvMetaProvider:             cmpvMetaProvider,
		k8sClusterConfigMetaProvider: k8sClusterConfigMetaProvider,
	}
}

// CreateCluster 创建集群
func (c *ClusterProvider) CreateCluster(request *coreentity.Request) error {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}

	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return fmt.Errorf("failed to create k8sClient: %w", err)
	}

	if err = verifyAddonExists(request, k8sClient); err != nil {
		return fmt.Errorf("failed to verify addon exists: %w", err)
	}

	clusterEntity, compEntityList, err := c.getEntityFromReq(request)
	if err != nil {
		return fmt.Errorf("failed to get cluster entity: %w", err)
	}

	clusterEntity.K8sClusterConfigID = k8sClusterConfig.ID
	addedClusterEntity, err := c.clusterMetaProvider.CreateCluster(clusterEntity)
	if err != nil {
		return fmt.Errorf("failed to create cluster: %w", err)
	}

	for _, compEntity := range compEntityList {
		compEntity.CrdClusterID = addedClusterEntity.ID
		_, err = c.componentMetaProvider.CreateComponent(compEntity)
		if err != nil {
			return fmt.Errorf("failed to create component: %w", err)
		}
	}

	if err = coreclient.CreateStorageAddonCluster(k8sClient, request); err != nil {
		return fmt.Errorf("failed to create cluster: %w", err)
	}
	return nil
}

// UpdateCluster 更新集群
func (c *ClusterProvider) UpdateCluster(request *coreentity.Request) error {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}

	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return fmt.Errorf("failed to create k8sClient: %w", err)
	}

	if err = verifyAddonExists(request, k8sClient); err != nil {
		return fmt.Errorf("failed to verify addon exists: %w", err)
	}

	clusterEntity, _, err := c.getEntityFromReq(request)
	if err != nil {
		return fmt.Errorf("failed to get cluster entity: %w", err)
	}

	clusterEntity.K8sClusterConfigID = k8sClusterConfig.ID

	// TODO 元数据变更记录

	if err = coreclient.UpdateStorageAddonCluster(k8sClient, request); err != nil {
		return fmt.Errorf("failed to update cluster: %w", err)
	}
	return nil
}

// DeleteCluster 删除集群
func (c *ClusterProvider) DeleteCluster(request *coreentity.Request) error {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return fmt.Errorf("failed to create k8sClient: %w", err)
	}
	params := map[string]interface{}{
		"cluster_name": request.ClusterName,
		"namespace":    request.Namespace,
	}
	clusterEntity, err := c.clusterMetaProvider.FindByParams(params)
	if err != nil {
		return err
	}
	_, err = c.clusterMetaProvider.DeleteClusterByID(clusterEntity.ID)
	if err != nil {
		return err
	}
	err = coreclient.DeleteStorageAddonCluster(k8sClient, request.ClusterName, request.Namespace)
	if err != nil {
		return err
	}
	return nil
}

// DescribeCluster 获取集群详情
func (c *ClusterProvider) DescribeCluster(request *coreentity.Request) (*coreentity.ClusterResponseData, error) {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}
	cluster, err := k8sClient.DynamicClient.
		Resource(kbtypes.ClusterGVR()).
		Namespace(request.Namespace).
		Get(context.TODO(), request.ClusterName, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}
	dataResponse, err := coreentity.GetClusterResponseData(cluster)
	if err != nil {
		return nil, err
	}
	return dataResponse, nil
}

// GetClusterStatus 获取集群状态
func (c *ClusterProvider) GetClusterStatus(request *coreentity.Request) (*coreentity.ClusterStatus, error) {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	cluster, err := k8sClient.DynamicClient.
		Resource(kbtypes.ClusterGVR()).
		Namespace(request.Namespace).
		Get(context.TODO(), request.ClusterName, metav1.GetOptions{})
	if err != nil {
		return nil, err
	}
	dataResponse, err := coreentity.GetClusterResponseData(cluster)
	if err != nil {
		return nil, err
	}
	return dataResponse.ClusterStatus, nil
}

// DescribeComponent 获取组件详情
func (c *ClusterProvider) DescribeComponent(request *coreentity.Request) (*coreentity.ComponentDetail, error) {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
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
			PodName:      pod.Name,
			Status:       pod.Status.Phase,
			Node:         pod.Spec.NodeName,
			Role:         role,
			CreateedTime: pod.CreationTimestamp.String(),
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

func (c *ClusterProvider) getEntityFromReq(request *coreentity.Request) (
	*providerentity.K8sCrdClusterEntity,
	[]*providerentity.K8sCrdComponentEntity,
	error,
) {
	clusterEntity := &providerentity.K8sCrdClusterEntity{
		ClusterName: request.ClusterName,
		Namespace:   request.Namespace,
		//Metadata:    string(metaDataJSON),
		//Spec:        string(specJson),
	}

	var compEntityList []*providerentity.K8sCrdComponentEntity
	for compTopoName := range request.ComponentMap {
		compName := request.Metadata.ClusterName + "-" + compTopoName
		componentEntity := &providerentity.K8sCrdComponentEntity{
			ComponentName: compName,
			//Metadata:      string(metaDataJSON),
			//Spec:          string(specJson),
		}
		compEntityList = append(compEntityList, componentEntity)
	}

	return clusterEntity, compEntityList, nil
}

func verifyAddonExists(request *coreentity.Request, k8sClient *coreclient.K8sClient) error {
	targetChartFullName := request.StorageAddonType + "-" + request.StorageAddonVersion
	isCreated, err := coreclient.StorageAddonIsCreated(k8sClient, targetChartFullName)
	if err != nil {
		return fmt.Errorf("failed to verify existence of storage addon chart %q: %w", targetChartFullName, err)
	}
	if !isCreated {
		return fmt.Errorf("storage addon chart %q does not exist", targetChartFullName)
	}
	return nil
}
