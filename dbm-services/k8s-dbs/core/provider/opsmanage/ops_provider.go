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

package opsmanage

import (
	"fmt"
	coreclient "k8s-dbs/core/client"
	coreentity "k8s-dbs/core/entity"
	serviceHelper "k8s-dbs/core/helper"
	"k8s-dbs/core/provider/clustermanage"
	metaprovider "k8s-dbs/metadata/provider"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
	"k8s.io/apimachinery/pkg/runtime"
)

// OpsRequestProvider the OpsRequest src struct
type OpsRequestProvider struct {
	opsRequestMetaProvider       metaprovider.K8sCrdOpsRequestProvider
	clusterMetaProvider          metaprovider.K8sCrdClusterProvider
	clusterMetaService           *clustermanage.ClusterProvider
	k8sClusterConfigMetaProvider metaprovider.K8sClusterConfigProvider
}

// NewOpsRequestService create a new OpsRequest src
func NewOpsRequestService(opsRequestMetaProvider metaprovider.K8sCrdOpsRequestProvider,
	clusterMetaProvider metaprovider.K8sCrdClusterProvider,
	clusterMetaService *clustermanage.ClusterProvider,
	k8sClusterConfigMetaProvider metaprovider.K8sClusterConfigProvider,
) *OpsRequestProvider {
	return &OpsRequestProvider{
		opsRequestMetaProvider:       opsRequestMetaProvider,
		clusterMetaProvider:          clusterMetaProvider,
		clusterMetaService:           clusterMetaService,
		k8sClusterConfigMetaProvider: k8sClusterConfigMetaProvider,
	}
}

// GetOpsRequestStatus get opsRequest status
func (o *OpsRequestProvider) GetOpsRequestStatus(request *coreentity.Request) (*coreentity.OpsRequestStatus, error) {
	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
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
	return responseData.OpsRequestStatus, nil
}

// VerticalScaling Create a verticalScaling of opsRequest
func (o *OpsRequestProvider) VerticalScaling(request *coreentity.Request) (*coreentity.Metadata, error) {
	verticalScaling, err := serviceHelper.CreateVerticalScalingObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(o.opsRequestMetaProvider, o.clusterMetaProvider, request, verticalScaling)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	err = coreclient.CreateCRD(k8sClient, verticalScaling)
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
	horizontalScaling, err := serviceHelper.CreateHorizontalScalingObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(o.opsRequestMetaProvider,
		o.clusterMetaProvider, request, horizontalScaling)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	err = coreclient.CreateCRD(k8sClient, horizontalScaling)
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
	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}
	crd := &coreentity.CustomResourceDefinition{
		ResourceName:         request.Metadata.ClusterName,
		Namespace:            request.Metadata.Namespace,
		GroupVersionResource: kbtypes.ClusterGVR(),
	}
	clusterCR, err := coreclient.GetCRD(k8sClient, crd)
	if err != nil {
		return nil, err
	}

	var clusterInfo *kbv1.Cluster
	err = runtime.DefaultUnstructuredConverter.FromUnstructured(clusterCR.Object, &clusterInfo)
	if err != nil {
		return nil, err
	}

	volumeExpansion, err := serviceHelper.CreateVolumeExpansionObject(request, clusterInfo)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(o.opsRequestMetaProvider, o.clusterMetaProvider, request, volumeExpansion)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, volumeExpansion)
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
	start, err := serviceHelper.CreateStartClusterObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(o.opsRequestMetaProvider, o.clusterMetaProvider, request, start)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
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
	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	if request.RestartList == nil {
		clusterResponseData, err := o.clusterMetaService.DescribeCluster(request)
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

	err = serviceHelper.CreateOpsRequestMetaData(o.opsRequestMetaProvider, o.clusterMetaProvider, request, restart)
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
	stop, err := serviceHelper.CreateStopClusterObject(request)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(o.opsRequestMetaProvider, o.clusterMetaProvider, request, stop)
	if err != nil {
		return nil, err
	}

	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
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
	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}
	crd := &coreentity.CustomResourceDefinition{
		ResourceName:         request.Metadata.ClusterName,
		Namespace:            request.Metadata.Namespace,
		GroupVersionResource: kbtypes.ClusterGVR(),
	}
	clusterCR, err := coreclient.GetCRD(k8sClient, crd)
	if err != nil {
		return nil, err
	}

	var clusterInfo *kbv1.Cluster
	err = runtime.DefaultUnstructuredConverter.FromUnstructured(clusterCR.Object, &clusterInfo)
	if err != nil {
		return nil, err
	}

	upgrade, err := serviceHelper.CreateUpgradeClusterObject(request, clusterInfo)
	if err != nil {
		return nil, err
	}

	err = serviceHelper.CreateOpsRequestMetaData(o.opsRequestMetaProvider, o.clusterMetaProvider, request, upgrade)
	if err != nil {
		return nil, err
	}

	err = coreclient.CreateCRD(k8sClient, upgrade)
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
	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
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

	err = serviceHelper.CreateOpsRequestMetaData(o.opsRequestMetaProvider, o.clusterMetaProvider, request, expose)
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
	k8sClusterConfig, err := o.k8sClusterConfigMetaProvider.FindConfigByName(request.K8sClusterName)
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
