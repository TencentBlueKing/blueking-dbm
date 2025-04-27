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
	client2 "k8s-dbs/core/client"
	entity2 "k8s-dbs/core/entity"
	provider2 "k8s-dbs/metadata/provider"
	"k8s-dbs/metadata/provider/entity"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ClusterProvider 集群管理核心服务
type ClusterProvider struct {
	clusterMetaProvider          provider2.K8sCrdClusterProvider
	componentMetaProvider        provider2.K8sCrdComponentProvider
	cdMetaProvider               provider2.K8sCrdClusterDefinitionProvider
	cmpdMetaProvider             provider2.K8sCrdCmpdProvider
	cmpvMetaProvider             provider2.K8sCrdCmpvProvider
	k8sClusterConfigMetaProvider provider2.K8sClusterConfigProvider
}

// NewClusterService 创建 ClusterProvider 实例
func NewClusterService(
	clusterMetaProvider provider2.K8sCrdClusterProvider,
	componentMetaProvider provider2.K8sCrdComponentProvider,
	cdMetaProvider provider2.K8sCrdClusterDefinitionProvider,
	cmpdMetaProvider provider2.K8sCrdCmpdProvider,
	cmpvMetaProvider provider2.K8sCrdCmpvProvider,
	k8sClusterConfigMetaProvider provider2.K8sClusterConfigProvider,
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
func (c *ClusterProvider) CreateCluster(request *entity2.Request) error {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}

	k8sClient, err := client2.NewK8sClient(k8sClusterConfig)
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

	if err = client2.CreateStorageAddonCluster(k8sClient, request); err != nil {
		return fmt.Errorf("failed to create cluster: %w", err)
	}
	return nil
}

// DeleteCluster 删除集群
func (c *ClusterProvider) DeleteCluster(request *entity2.Request) error {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := client2.NewK8sClient(k8sClusterConfig)

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
	err = client2.DeleteStorageAddonCluster(k8sClient, request.ClusterName, request.Namespace)
	if err != nil {
		return err
	}
	return nil
}

// DescribeCluster 获取集群详情
func (c *ClusterProvider) DescribeCluster(request *entity2.Request) (*entity2.ClusterResponseData, error) {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := client2.NewK8sClient(k8sClusterConfig)

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
	dataResponse, err := entity2.GetClusterResponseData(cluster)
	if err != nil {
		return nil, err
	}
	return dataResponse, nil
}

// GetClusterStatus 获取集群状态
func (c *ClusterProvider) GetClusterStatus(request *entity2.Request) (*entity2.ClusterStatus, error) {
	k8sClusterConfig, err := c.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := client2.NewK8sClient(k8sClusterConfig)

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
	dataResponse, err := entity2.GetClusterResponseData(cluster)
	if err != nil {
		return nil, err
	}
	return dataResponse.ClusterStatus, nil
}

func (c *ClusterProvider) getEntityFromReq(request *entity2.Request) (
	*entity.K8sCrdClusterEntity,
	[]*entity.K8sCrdComponentEntity,
	error,
) {
	clusterEntity := &entity.K8sCrdClusterEntity{
		ClusterName: request.ClusterName,
		Namespace:   request.Namespace,
		//Metadata:    string(metaDataJSON),
		//Spec:        string(specJson),
	}

	var compEntityList []*entity.K8sCrdComponentEntity
	for compTopoName := range request.ComponentMap {
		compName := request.Metadata.ClusterName + "-" + compTopoName
		componentEntity := &entity.K8sCrdComponentEntity{
			ComponentName: compName,
			//Metadata:      string(metaDataJSON),
			//Spec:          string(specJson),
		}
		compEntityList = append(compEntityList, componentEntity)
	}

	return clusterEntity, compEntityList, nil
}

func verifyAddonExists(request *entity2.Request, k8sClient *client2.K8sClient) error {
	targetChartFullName := request.StorageAddonType + "-" + request.StorageAddonVersion
	isCreated, err := client2.StorageAddonIsCreated(k8sClient, targetChartFullName)
	if err != nil {
		return fmt.Errorf("failed to verify existence of storage addon chart %q: %w", targetChartFullName, err)
	}
	if !isCreated {
		return fmt.Errorf("storage addon chart %q does not exist", targetChartFullName)
	}
	return nil
}
