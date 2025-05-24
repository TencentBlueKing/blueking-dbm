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
	"encoding/json"
	"fmt"
	"k8s-dbs/common/utils"
	coreclient "k8s-dbs/core/client"
	clientconst "k8s-dbs/core/client/constants"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	metaprovider "k8s-dbs/metadata/provider"
	providerentity "k8s-dbs/metadata/provider/entity"
	"log/slog"
	"slices"

	"github.com/pkg/errors"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

// ClusterProvider 集群管理核心服务
type ClusterProvider struct {
	clusterMetaProvider   metaprovider.K8sCrdClusterProvider
	componentMetaProvider metaprovider.K8sCrdComponentProvider
	cdMetaProvider        metaprovider.K8sCrdClusterDefinitionProvider
	cmpdMetaProvider      metaprovider.K8sCrdCmpdProvider
	cmpvMetaProvider      metaprovider.K8sCrdCmpvProvider
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
	reqRecordProvider     metaprovider.ClusterRequestRecordProvider
	releaseMetaProvider   metaprovider.AddonClusterReleaseProvider
}

// ClusterProviderBuilder ClusterProvider builder
type ClusterProviderBuilder struct {
	clusterMetaProvider   metaprovider.K8sCrdClusterProvider
	componentMetaProvider metaprovider.K8sCrdComponentProvider
	cdMetaProvider        metaprovider.K8sCrdClusterDefinitionProvider
	cmpdMetaProvider      metaprovider.K8sCrdCmpdProvider
	cmpvMetaProvider      metaprovider.K8sCrdCmpvProvider
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
	reqRecordProvider     metaprovider.ClusterRequestRecordProvider
	releaseMetaProvider   metaprovider.AddonClusterReleaseProvider
}

// NewClusterProviderBuilder 创建 ClusterProviderBuilder 实例
func NewClusterProviderBuilder() *ClusterProviderBuilder {
	return &ClusterProviderBuilder{}
}

// WithClusterMetaProvider 设置 ClusterMetaProvider
func (c *ClusterProviderBuilder) WithClusterMetaProvider(p metaprovider.K8sCrdClusterProvider) *ClusterProviderBuilder {
	c.clusterMetaProvider = p
	return c
}

// WithComponentMetaProvider 设置 ComponentMetaProvider
func (c *ClusterProviderBuilder) WithComponentMetaProvider(
	p metaprovider.K8sCrdComponentProvider,
) *ClusterProviderBuilder {
	c.componentMetaProvider = p
	return c
}

// WithCdMetaProvider 设置 CdMetaProvider
func (c *ClusterProviderBuilder) WithCdMetaProvider(
	p metaprovider.K8sCrdClusterDefinitionProvider,
) *ClusterProviderBuilder {
	c.cdMetaProvider = p
	return c
}

// WithCmpdMetaProvider 设置 CmpdMetaProvider
func (c *ClusterProviderBuilder) WithCmpdMetaProvider(p metaprovider.K8sCrdCmpdProvider) *ClusterProviderBuilder {
	c.cmpdMetaProvider = p
	return c
}

// WithCmpvMetaProvider 设置 CmpvMetaProvider
func (c *ClusterProviderBuilder) WithCmpvMetaProvider(p metaprovider.K8sCrdCmpvProvider) *ClusterProviderBuilder {
	c.cmpvMetaProvider = p
	return c
}

// WithClusterConfigMetaProvider 设置 ClusterConfigMetaProvider
func (c *ClusterProviderBuilder) WithClusterConfigMetaProvider(
	p metaprovider.K8sClusterConfigProvider,
) *ClusterProviderBuilder {
	c.clusterConfigProvider = p
	return c
}

// WithReqRecordProvider 设置 ReqRecordProvider
func (c *ClusterProviderBuilder) WithReqRecordProvider(
	p metaprovider.ClusterRequestRecordProvider,
) *ClusterProviderBuilder {
	c.reqRecordProvider = p
	return c
}

// WithReleaseMetaProvider 设置 ReleaseMetaProvider
func (c *ClusterProviderBuilder) WithReleaseMetaProvider(
	p metaprovider.AddonClusterReleaseProvider,
) *ClusterProviderBuilder {
	c.releaseMetaProvider = p
	return c
}

// Build 构建并返回 ClusterProvider 实例
func (c *ClusterProviderBuilder) Build() (*ClusterProvider, error) {
	if c.clusterMetaProvider == nil {
		return nil, errors.New("clusterMetaProvider is required")
	}
	if c.componentMetaProvider == nil {
		return nil, errors.New("componentMetaProvider is required")
	}
	if c.cdMetaProvider == nil {
		return nil, errors.New("cdMetaProvider is required")
	}
	if c.cmpdMetaProvider == nil {
		return nil, errors.New("cmpdMetaProvider is required")
	}
	if c.cmpvMetaProvider == nil {
		return nil, errors.New("cmpvMetaProvider is required")
	}
	if c.clusterConfigProvider == nil {
		return nil, errors.New("clusterConfigProvider is required")
	}
	if c.reqRecordProvider == nil {
		return nil, errors.New("reqRecordProvider is required")
	}
	if c.releaseMetaProvider == nil {
		return nil, errors.New("releaseMetaProvider is required")
	}
	return &ClusterProvider{
		clusterMetaProvider:   c.clusterMetaProvider,
		componentMetaProvider: c.componentMetaProvider,
		cdMetaProvider:        c.cdMetaProvider,
		cmpdMetaProvider:      c.cmpdMetaProvider,
		cmpvMetaProvider:      c.cmpvMetaProvider,
		clusterConfigProvider: c.clusterConfigProvider,
		reqRecordProvider:     c.reqRecordProvider,
		releaseMetaProvider:   c.releaseMetaProvider,
	}, nil
}

// CreateCluster 创建集群
func (c *ClusterProvider) CreateCluster(request *coreentity.Request) error {
	addedRequestEntity, err := c.createRequestEntity(request, coreconst.CreateCluster)
	if err != nil {
		return fmt.Errorf("failed to create request entity: %w", err)
	}

	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8s cluster config for name %q: %w", request.K8sClusterName, err)

	}

	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return fmt.Errorf("failed to create k8s client for cluster %q: %w", request.K8sClusterName, err)

	}

	if err = verifyAddonExists(request, k8sClient); err != nil {
		return fmt.Errorf("addon verification failed for cluster %q: %w", request.ClusterName, err)

	}

	addedClusterEntity, err := c.createClusterEntity(request, addedRequestEntity.RequestID, k8sClusterConfig.ID)
	if err != nil {
		return fmt.Errorf("failed to create cluster entity: %w", err)
	}

	_, err = c.createComponentEntity(request, addedClusterEntity.ID)
	if err != nil {
		return fmt.Errorf("failed to create component entity for cluster %q: %w", request.ClusterName, err)

	}

	releaseValues, err := coreclient.CreateStorageAddonCluster(k8sClient, request)
	if err != nil {
		slog.Error("failed to create storage addon cluster",
			"cluster_name", request.ClusterName,
			"namespace", request.Namespace,
			"error", err,
		)
		return fmt.Errorf("failed to create storage addon cluster: %w", err)
	}

	// 7. 构建并保存 release 实体
	clusterRelease, err := buildClusterReleaseEntity(
		k8sClusterConfig.ID,
		request,
		coreconst.DefaultUserName,
		coreconst.DefaultRepoName,
		coreconst.DefaultRepoRepository,
		releaseValues,
	)
	if err != nil {
		slog.Error("create cluster release entity error", "error", err.Error())
		return err
	}
	_, err = c.releaseMetaProvider.CreateClusterRelease(clusterRelease)
	if err != nil {
		slog.Error("failed to save cluster release",
			"release_name", request.ClusterName,
			"namespace", request.Namespace,
			"error", err,
		)
		return fmt.Errorf("failed to save cluster release: %w", err)
	}
	return nil
}

// UpdateCluster 更新集群
func (c *ClusterProvider) UpdateCluster(request *coreentity.Request) error {
	_, err := c.createRequestEntity(request, coreconst.UpdateCluster)
	if err != nil {
		return err
	}

	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
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

	// TODO 元数据变更记录

	if err = coreclient.UpdateStorageAddonCluster(k8sClient, request); err != nil {
		return fmt.Errorf("failed to update cluster: %w", err)
	}
	return nil
}

// DeleteCluster 删除集群
func (c *ClusterProvider) DeleteCluster(request *coreentity.Request) error {
	_, err := c.createRequestEntity(request, coreconst.DeleteCluster)
	if err != nil {
		return err
	}

	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
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
	dataResponse, err := c.getClusterDataResp(request)
	if err != nil {
		return nil, err
	}
	return dataResponse, nil
}

// GetClusterStatus 获取集群状态
func (c *ClusterProvider) GetClusterStatus(request *coreentity.Request) (*coreentity.ClusterStatus, error) {
	dataResponse, err := c.getClusterDataResp(request)
	if err != nil {
		return nil, err
	}
	return dataResponse.ClusterStatus, nil
}

// DescribeComponent 获取组件详情
func (c *ClusterProvider) DescribeComponent(request *coreentity.Request) (*coreentity.ComponentDetail, error) {
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

// createRequestEntity Save the request instance
func (c *ClusterProvider) createRequestEntity(
	request *coreentity.Request,
	requestType string,
) (*providerentity.ClusterRequestRecordEntity, error) {
	requestBytes, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("serialization request failed: %v", err)
	}

	requestRecord := &providerentity.ClusterRequestRecordEntity{
		RequestID:     utils.RequestID(),
		RequestType:   requestType,
		RequestParams: string(requestBytes),
	}

	addedRequestRecord, err := c.reqRecordProvider.CreateRequestRecord(requestRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create request entity: %w", err)
	}
	return addedRequestRecord, nil
}

// createClusterEntity Save and return the cluster instance
func (c *ClusterProvider) createClusterEntity(
	request *coreentity.Request,
	requestID string,
	k8sClusterConfigID uint64,
) (*providerentity.K8sCrdClusterEntity, error) {
	clusterEntity := &providerentity.K8sCrdClusterEntity{
		ClusterName:        request.ClusterName,
		Namespace:          request.Namespace,
		RequestID:          requestID,
		K8sClusterConfigID: k8sClusterConfigID,
	}
	addedClusterEntity, err := c.clusterMetaProvider.CreateCluster(clusterEntity)
	if err != nil {
		return nil, fmt.Errorf("failed to create cluster entity: %w", err)
	}

	return addedClusterEntity, nil
}

// createComponentEntity Save and return an array of component instances
func (c *ClusterProvider) createComponentEntity(
	request *coreentity.Request,
	crdClusterID uint64,
) ([]*providerentity.K8sCrdComponentEntity, error) {
	var compEntityList []*providerentity.K8sCrdComponentEntity
	for compTopoName := range request.ComponentMap {
		compName := request.Metadata.ClusterName + "-" + compTopoName
		componentEntity := &providerentity.K8sCrdComponentEntity{
			ComponentName: compName,
			CrdClusterID:  crdClusterID,
		}
		_, err := c.componentMetaProvider.CreateComponent(componentEntity)
		if err != nil {
			return nil, fmt.Errorf("failed to create component entity %s : %w", compName, err)
		}
		compEntityList = append(compEntityList, componentEntity)
	}
	return compEntityList, nil
}

// verifyAddonExists Determine whether the Addon of the storage cluster exists
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

// getClusterDataResp Get cluster details
func (c *ClusterProvider) getClusterDataResp(request *coreentity.Request) (*coreentity.ClusterResponseData, error) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
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

// buildClusterReleaseEntity 构建 ClusterRelease 实体
func buildClusterReleaseEntity(
	k8sClusterConfigID uint64,
	request *coreentity.Request,
	createdBy string,
	repoName string,
	repoRepository string,
	releaseValues map[string]interface{},
) (*providerentity.AddonClusterReleaseEntity, error) {
	releaseName := request.ClusterName
	namespace := request.Namespace
	chartName := request.StorageAddonType + "-cluster"
	chartVersion := request.StorageAddonVersion

	jsonData, err := json.Marshal(releaseValues)
	if err != nil {
		slog.Error("failed to marshal release values",
			"release_name", releaseName,
			"error", err,
		)
		return nil, fmt.Errorf("failed to marshal release values: %w", err)
	}

	jsonStr := string(jsonData)

	return &providerentity.AddonClusterReleaseEntity{
		K8sClusterConfigID: k8sClusterConfigID,
		ReleaseName:        releaseName,
		CreatedBy:          createdBy,
		Namespace:          namespace,
		ChartName:          chartName,
		ChartVersion:       chartVersion,
		RepoName:           repoName,
		RepoRepository:     repoRepository,
		ChartValues:        jsonStr,
	}, nil
}
