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
	"encoding/json"
	"errors"
	"fmt"
	"k8s-dbs/common/util"
	coreclient "k8s-dbs/core/client"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	serviceHelper "k8s-dbs/core/helper"
	metaprovider "k8s-dbs/metadata/provider"
	providerentity "k8s-dbs/metadata/provider/entity"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
	"k8s.io/apimachinery/pkg/runtime"
)

// OpsRequestProvider the OpsRequest provider struct
type OpsRequestProvider struct {
	opsRequestMetaProvider metaprovider.K8sCrdOpsRequestProvider
	clusterMetaProvider    metaprovider.K8sCrdClusterProvider
	clusterProvider        *ClusterProvider
	clusterConfigProvider  metaprovider.K8sClusterConfigProvider
	reqRecordProvider      metaprovider.ClusterRequestRecordProvider
	releaseMetaProvider    metaprovider.AddonClusterReleaseProvider
}

// NewOpsReqProviderBuilder 创建 OpsReqProviderBuilder 实例
func NewOpsReqProviderBuilder() *OpsReqProviderBuilder {
	return &OpsReqProviderBuilder{}
}

// OpsReqProviderBuilder ClusterProvider builder
type OpsReqProviderBuilder struct {
	opsRequestMetaProvider metaprovider.K8sCrdOpsRequestProvider
	clusterMetaProvider    metaprovider.K8sCrdClusterProvider
	clusterConfigProvider  metaprovider.K8sClusterConfigProvider
	reqRecordProvider      metaprovider.ClusterRequestRecordProvider
	releaseMetaProvider    metaprovider.AddonClusterReleaseProvider
	clusterProvider        *ClusterProvider
}

// WithopsRequestMetaProvider 设置 opsRequestMetaProvider
func (o *OpsReqProviderBuilder) WithopsRequestMetaProvider(
	p metaprovider.K8sCrdOpsRequestProvider,
) *OpsReqProviderBuilder {
	o.opsRequestMetaProvider = p
	return o
}

// WithClusterMetaProvider 设置 ClusterMetaProvider
func (o *OpsReqProviderBuilder) WithClusterMetaProvider(p metaprovider.K8sCrdClusterProvider) *OpsReqProviderBuilder {
	o.clusterMetaProvider = p
	return o
}

// WithClusterConfigMetaProvider 设置 ClusterConfigMetaProvider
func (o *OpsReqProviderBuilder) WithClusterConfigMetaProvider(
	p metaprovider.K8sClusterConfigProvider,
) *OpsReqProviderBuilder {
	o.clusterConfigProvider = p
	return o
}

// WithReqRecordProvider 设置 ReqRecordProvider
func (o *OpsReqProviderBuilder) WithReqRecordProvider(
	p metaprovider.ClusterRequestRecordProvider,
) *OpsReqProviderBuilder {
	o.reqRecordProvider = p
	return o
}

// WithReleaseMetaProvider 设置 ReleaseMetaProvider
func (o *OpsReqProviderBuilder) WithReleaseMetaProvider(
	p metaprovider.AddonClusterReleaseProvider,
) *OpsReqProviderBuilder {
	o.releaseMetaProvider = p
	return o
}

// WithClusterProvider 设置 ClusterProvider
func (o *OpsReqProviderBuilder) WithClusterProvider(p *ClusterProvider) *OpsReqProviderBuilder {
	o.clusterProvider = p
	return o
}

// Build 构建并返回 OpsRequestProvider 实例
func (o *OpsReqProviderBuilder) Build() (*OpsRequestProvider, error) {
	if o.opsRequestMetaProvider == nil {
		return nil, errors.New("opsRequestMetaProvider is required")
	}
	if o.clusterMetaProvider == nil {
		return nil, errors.New("clusterMetaProvider is required")
	}
	if o.clusterConfigProvider == nil {
		return nil, errors.New("clusterConfigProvider is required")
	}
	if o.reqRecordProvider == nil {
		return nil, errors.New("reqRecordProvider is required")
	}
	if o.releaseMetaProvider == nil {
		return nil, errors.New("releaseMetaProvider is required")
	}
	if o.clusterProvider == nil {
		return nil, errors.New("clusterProvider is required")
	}
	return &OpsRequestProvider{
		opsRequestMetaProvider: o.opsRequestMetaProvider,
		clusterMetaProvider:    o.clusterMetaProvider,
		clusterConfigProvider:  o.clusterConfigProvider,
		reqRecordProvider:      o.reqRecordProvider,
		releaseMetaProvider:    o.releaseMetaProvider,
		clusterProvider:        o.clusterProvider,
	}, nil
}

// GetOpsRequestStatus get opsRequest status
func (o *OpsRequestProvider) GetOpsRequestStatus(request *coreentity.Request) (*coreentity.OpsRequestStatus, error) {
	responseData, err := o.DescribeOpsRequest(request)
	if err != nil {
		return nil, err
	}
	return responseData.OpsRequestStatus, nil
}

// VerticalScaling Create a verticalScaling of opsRequest
func (o *OpsRequestProvider) VerticalScaling(request *coreentity.Request) (*coreentity.Metadata, error) {
	addedRequestEntity, err := o.createRequestEntity(request, coreconst.VScaling)
	if err != nil {
		return nil, err
	}

	// Get the configuration of the k8s client based on the unique identifier and initialize the client
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	verticalScaling, err := serviceHelper.CreateVerticalScalingObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(
		o.opsRequestMetaProvider,
		o.clusterMetaProvider,
		request,
		verticalScaling,
		addedRequestEntity.RequestID,
		k8sClusterConfig.ID,
	)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, verticalScaling)
	if err != nil {
		return nil, err
	}

	_, err = serviceHelper.UpdateValWithCompList(o.releaseMetaProvider, request, k8sClusterConfig.ID)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(verticalScaling.ResourceObject)
	if err != nil {
		return nil, err
	}
	return &responseData.Metadata, nil
}

// HorizontalScaling Create a horizontalScaling of opsRequest
func (o *OpsRequestProvider) HorizontalScaling(request *coreentity.Request) (*coreentity.Metadata, error) {
	addedRequestEntity, err := o.createRequestEntity(request, coreconst.HScaling)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	horizontalScaling, err := serviceHelper.CreateHorizontalScalingObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(
		o.opsRequestMetaProvider,
		o.clusterMetaProvider,
		request,
		horizontalScaling,
		addedRequestEntity.RequestID,
		k8sClusterConfig.ID,
	)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, horizontalScaling)
	if err != nil {
		return nil, err
	}

	paramsRelease := map[string]interface{}{
		"k8s_cluster_config_id": k8sClusterConfig.ID,
		"release_name":          request.ClusterName,
		"namespace":             request.Namespace,
	}
	releaseEntity, err := o.releaseMetaProvider.FindByParams(paramsRelease)
	if err != nil {
		return nil, err
	}
	newReleaseEntity, err := serviceHelper.UpdateValWithHScaling(request, releaseEntity)
	if err != nil {
		return nil, err
	}
	_, err = o.releaseMetaProvider.UpdateClusterRelease(newReleaseEntity)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(horizontalScaling.ResourceObject)
	if err != nil {
		return nil, err
	}

	return &responseData.Metadata, nil
}

// VolumeExpansion Create a volumeExpansion of opsRequest
func (o *OpsRequestProvider) VolumeExpansion(request *coreentity.Request) (*coreentity.Metadata, error) {
	addedRequestEntity, err := o.createRequestEntity(request, coreconst.VExpansion)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	clusterInfo, err := getClusterInfo(request, k8sClient)
	if err != nil {
		return nil, err
	}

	volumeExpansion, err := serviceHelper.CreateVolumeExpansionObject(request, clusterInfo)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(
		o.opsRequestMetaProvider,
		o.clusterMetaProvider,
		request,
		volumeExpansion,
		addedRequestEntity.RequestID,
		k8sClusterConfig.ID,
	)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, volumeExpansion)
	if err != nil {
		return nil, err
	}

	_, err = serviceHelper.UpdateValWithCompList(o.releaseMetaProvider, request, k8sClusterConfig.ID)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(volumeExpansion.ResourceObject)
	if err != nil {
		return nil, err
	}
	return &responseData.Metadata, nil
}

// StartCluster Create a startCluster of opsRequest
func (o *OpsRequestProvider) StartCluster(request *coreentity.Request) (*coreentity.Metadata, error) {
	requestType := coreconst.StartCluster
	if request.ComponentList != nil {
		requestType = coreconst.StartComp
	}
	addedRequestEntity, err := o.createRequestEntity(request, requestType)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	start, err := serviceHelper.CreateStartClusterObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(
		o.opsRequestMetaProvider,
		o.clusterMetaProvider,
		request,
		start,
		addedRequestEntity.RequestID,
		k8sClusterConfig.ID,
	)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, start)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(start.ResourceObject)
	if err != nil {
		return nil, err
	}

	return &responseData.Metadata, nil
}

// RestartCluster Create a restartCluster of opsRequest
func (o *OpsRequestProvider) RestartCluster(request *coreentity.Request) (*coreentity.Metadata, error) {
	requestType := coreconst.RestartCluster
	if request.ComponentList != nil {
		requestType = coreconst.RestartComp
	}

	addedRequestEntity, err := o.createRequestEntity(request, requestType)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	if request.RestartList == nil {
		clusterResponseData, err := o.clusterProvider.DescribeCluster(request)
		if err != nil {
			return nil, err
		}
		for _, comp := range clusterResponseData.Spec.ComponentList {
			request.RestartList = append(request.RestartList, opv1.ComponentOps{ComponentName: comp.ComponentName})
		}
	}
	restart, err := serviceHelper.CreateRestartClusterObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(
		o.opsRequestMetaProvider,
		o.clusterMetaProvider,
		request,
		restart,
		addedRequestEntity.RequestID,
		k8sClusterConfig.ID,
	)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, restart)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(restart.ResourceObject)
	if err != nil {
		return nil, err
	}
	return &responseData.Metadata, nil
}

// StopCluster Create a stopCluster of opsRequest
func (o *OpsRequestProvider) StopCluster(request *coreentity.Request) (*coreentity.Metadata, error) {
	requestType := coreconst.StopCluster
	if request.ComponentList != nil {
		requestType = coreconst.StopComp
	}

	addedRequestEntity, err := o.createRequestEntity(request, requestType)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	stop, err := serviceHelper.CreateStopClusterObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(
		o.opsRequestMetaProvider,
		o.clusterMetaProvider,
		request,
		stop,
		addedRequestEntity.RequestID,
		k8sClusterConfig.ID,
	)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, stop)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(stop.ResourceObject)
	if err != nil {
		return nil, err
	}

	return &responseData.Metadata, nil
}

// UpgradeCluster create crd if needed and Create a upgradeCluster of opsRequest
func (o *OpsRequestProvider) UpgradeCluster(request *coreentity.Request) (*coreentity.Metadata, error) {
	addedRequestEntity, err := o.createRequestEntity(request, coreconst.UpgradeComp)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, err
	}

	clusterInfo, err := getClusterInfo(request, k8sClient)
	if err != nil {
		return nil, err
	}

	upgrade, err := serviceHelper.CreateUpgradeClusterObject(request, clusterInfo)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(
		o.opsRequestMetaProvider,
		o.clusterMetaProvider,
		request,
		upgrade,
		addedRequestEntity.RequestID,
		k8sClusterConfig.ID,
	)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, upgrade)
	if err != nil {
		return nil, err
	}

	_, err = serviceHelper.UpdateValWithCompList(o.releaseMetaProvider, request, k8sClusterConfig.ID)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(upgrade.ResourceObject)
	if err != nil {
		return nil, err
	}
	return &responseData.Metadata, nil
}

// ExposeCluster create crd if needed and Create a exposeCluster of opsRequest
func (o *OpsRequestProvider) ExposeCluster(request *coreentity.Request) (*coreentity.Metadata, error) {
	addedRequestEntity, err := o.createRequestEntity(request, coreconst.ExposeService)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	expose, err := serviceHelper.CreateExposeClusterObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(
		o.opsRequestMetaProvider,
		o.clusterMetaProvider,
		request,
		expose,
		addedRequestEntity.RequestID,
		k8sClusterConfig.ID,
	)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, expose)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(expose.ResourceObject)
	if err != nil {
		return nil, err
	}
	return &responseData.Metadata, nil
}

// DescribeOpsRequest describe OpsRequest
func (o *OpsRequestProvider) DescribeOpsRequest(request *coreentity.Request) (*coreentity.OpsRequestData, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}
	crd := &coreentity.CustomResourceDefinition{
		ResourceName:         request.Metadata.OpsRequestName,
		Namespace:            request.Metadata.Namespace,
		GroupVersionResource: kbtypes.OpsGVR(),
	}
	opsRequest, err := coreclient.GetCRD(k8sClient, crd)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(opsRequest)
	if err != nil {
		return nil, err
	}
	return responseData, nil
}

// createRequestEntity Save and return the request instance
func (o *OpsRequestProvider) createRequestEntity(
	request *coreentity.Request,
	requestType string,
) (*providerentity.ClusterRequestRecordEntity, error) {
	// Serialize request
	requestBytes, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("serialization request failed: %v", err)
	}

	// Construct a request instance object
	requestRecord := &providerentity.ClusterRequestRecordEntity{
		RequestID:     util.RequestID(),
		RequestType:   requestType,
		RequestParams: string(requestBytes),
	}

	addedRequestRecord, err := o.reqRecordProvider.CreateRequestRecord(requestRecord)
	if err != nil {
		return nil, fmt.Errorf("failed to create request entity: %w", err)
	}
	return addedRequestRecord, nil
}

// getClusterInfo Query cluster information and return
func getClusterInfo(request *coreentity.Request, k8sClient *coreclient.K8sClient) (*kbv1.Cluster, error) {
	// Construct and query crd resources
	crd := &coreentity.CustomResourceDefinition{
		ResourceName:         request.Metadata.ClusterName,
		Namespace:            request.Metadata.Namespace,
		GroupVersionResource: kbtypes.ClusterGVR(),
	}
	clusterCR, err := coreclient.GetCRD(k8sClient, crd)
	if err != nil {
		return nil, err
	}
	// Serializing Unstructured Format
	var clusterInfo *kbv1.Cluster
	err = runtime.DefaultUnstructuredConverter.FromUnstructured(clusterCR.Object, &clusterInfo)
	if err != nil {
		return nil, err
	}
	return clusterInfo, nil
}
