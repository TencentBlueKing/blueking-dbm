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
	commentity "k8s-dbs/common/entity"
	commutil "k8s-dbs/common/util"
	coreentity "k8s-dbs/core/entity"
	coreutil "k8s-dbs/core/util"
	"k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	metautil "k8s-dbs/metadata/util"
	"log/slog"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
	"k8s.io/apimachinery/pkg/runtime"

	addonopschecker "k8s-dbs/core/checker/addonoperation"
)

// OpsRequestProvider the OpsRequest provider struct
type OpsRequestProvider struct {
	opsRequestProvider    metaprovider.K8sCrdOpsRequestProvider
	clusterMetaProvider   metaprovider.K8sCrdClusterProvider
	clusterProvider       *ClusterProvider
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
	reqRecordProvider     metaprovider.ClusterRequestRecordProvider
	releaseMetaProvider   metaprovider.AddonClusterReleaseProvider
}

// OpsRequestProviderOption OpsRequestProvider 的函数选项
type OpsRequestProviderOption func(*OpsRequestProvider)

// OpsRequestProviderBuilder 辅助构建 OpsRequestProvider
type OpsRequestProviderBuilder struct{}

// NewOpsReqProvider 创建 OpsReqProvider 实例
func NewOpsReqProvider(opts ...OpsRequestProviderOption) (*OpsRequestProvider, error) {
	provider := &OpsRequestProvider{}
	for _, opt := range opts {
		opt(provider)
	}
	if err := provider.validateProvider(); err != nil {
		slog.Error("failed to validate ops request provider", "error", err)
		return nil, err
	}
	return provider, nil
}

// WithOpsRequestMeta 设置 opsRequestProvider
func (o *OpsRequestProviderBuilder) WithOpsRequestMeta(
	provider metaprovider.K8sCrdOpsRequestProvider,
) OpsRequestProviderOption {
	return func(p *OpsRequestProvider) {
		p.opsRequestProvider = provider
	}
}

// WithClusterMeta 设置 ClusterMetaProvider
func (o *OpsRequestProviderBuilder) WithClusterMeta(
	provider metaprovider.K8sCrdClusterProvider,
) OpsRequestProviderOption {
	return func(p *OpsRequestProvider) {
		p.clusterMetaProvider = provider
	}
}

// WithClusterConfigMeta 设置 ClusterConfigMetaProvider
func (o *OpsRequestProviderBuilder) WithClusterConfigMeta(
	provider metaprovider.K8sClusterConfigProvider,
) OpsRequestProviderOption {
	return func(p *OpsRequestProvider) {
		p.clusterConfigProvider = provider
	}
}

// WithReqRecordMeta 设置 reqRecordProvider
func (o *OpsRequestProviderBuilder) WithReqRecordMeta(
	provider metaprovider.ClusterRequestRecordProvider,
) OpsRequestProviderOption {
	return func(p *OpsRequestProvider) {
		p.reqRecordProvider = provider
	}
}

// WithReleaseMeta 设置 ReleaseMetaProvider
func (o *OpsRequestProviderBuilder) WithReleaseMeta(
	provider metaprovider.AddonClusterReleaseProvider,
) OpsRequestProviderOption {
	return func(p *OpsRequestProvider) {
		p.releaseMetaProvider = provider
	}
}

// WithClusterProvider 设置 ClusterProvider
func (o *OpsRequestProviderBuilder) WithClusterProvider(
	provider *ClusterProvider,
) OpsRequestProviderOption {
	return func(p *OpsRequestProvider) {
		p.clusterProvider = provider
	}
}

// ClusterOperationFn 集群运维操作函数定义
type ClusterOperationFn func(*commentity.DbsContext, *coreentity.Request) (*coreentity.Metadata, error)

// ReleaseMetaUpdateFn 集群 Release 元数据更新函数定义
type ReleaseMetaUpdateFn func(provider metaprovider.AddonClusterReleaseProvider,
	request *coreentity.Request,
	k8sClusterConfigID uint64) (*metaentity.AddonClusterReleaseEntity, error)

// withMetaDataSync 同步元数据信息变更
func (o *OpsRequestProvider) withMetaDataSync(
	dbsCtx *commentity.DbsContext,
	request *coreentity.Request,
	clusterOpsFn ClusterOperationFn,
	releaseUpdateFn ReleaseMetaUpdateFn,
) (*coreentity.Metadata, error) {
	// 记录审计日志
	addedRequestEntity, err := metautil.SaveAuditLog(o.reqRecordProvider, request, dbsCtx.RequestType)
	if err != nil {
		return nil, err
	}
	dbsCtx.RequestID = addedRequestEntity.RequestID

	// 执行集群运维操作
	result, err := clusterOpsFn(dbsCtx, request)
	if err != nil {
		return nil, err
	}

	if releaseUpdateFn != nil {
		// 更新集群 release 记录
		_, err = releaseUpdateFn(o.releaseMetaProvider, request, dbsCtx.K8sClusterConfigID)
		if err != nil {
			return nil, err
		}
	}

	// 更新集群 cluster 记录
	if err = metautil.UpdateClusterLastUpdated(o.clusterMetaProvider, dbsCtx, request); err != nil {
		return nil, err
	}
	return result, nil
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
func (o *OpsRequestProvider) VerticalScaling(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	return o.withMetaDataSync(ctx, request, o.doVerticalScaling, metautil.UpdateValWithCompList)
}

// doVerticalScaling 垂直扩容具体实现
func (o *OpsRequestProvider) doVerticalScaling(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateK8sClientError, err)
	}

	verticalScaling, err := coreutil.CreateVerticalScalingObject(request)
	if err != nil {
		return nil, err
	}

	if err = metautil.CreateOpsRequestMetaData(
		o.opsRequestProvider,
		o.clusterMetaProvider,
		request,
		verticalScaling,
		ctx.RequestID,
		k8sClusterConfig.ID,
	); err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateMetaDataError, err)
	}

	if err = coreutil.CreateCRD(k8sClient, verticalScaling); err != nil {
		return nil, fmt.Errorf("下发垂直扩容任务失败: %w", err)
	}

	responseData, err := coreentity.GetOpsRequestData(verticalScaling.ResourceObject)
	if err != nil {
		return nil, fmt.Errorf("获取垂直扩容任务详情失败: %w", err)
	}
	return &responseData.Metadata, nil
}

// HorizontalScaling 水平扩容装饰方法
func (o *OpsRequestProvider) HorizontalScaling(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	clusterEntity, err := o.checkClusterExists(ctx, request)
	if err != nil {
		return nil, err
	}
	for _, component := range request.HorizontalScalingList {
		checkResult, err := addonopschecker.ComponentOpsChecker.Check(
			ctx,
			addonopschecker.AddonType(clusterEntity.AddonInfo.AddonType),
			addonopschecker.AddonComponent(component.ComponentName),
			addonopschecker.OperationType(ctx.RequestType),
			request,
		)
		if err != nil || !checkResult {
			return nil, err
		}
	}

	return o.withMetaDataSync(ctx, request, o.doHorizontalScaling, metautil.UpdateValWithHScaling)
}

// checkClusterExists 检查集群是否存在
func (o *OpsRequestProvider) checkClusterExists(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*metaentity.K8sCrdClusterEntity, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError,
			fmt.Errorf("未找到对应的 k8s 集群信息,集群名称:%s, 错误详情:%w", request.K8sClusterName, err))
	}
	ctx.K8sClusterConfig = k8sClusterConfig
	clusterEntity, err := o.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		K8sClusterConfigID: k8sClusterConfig.ID,
		ClusterName:        request.ClusterName,
		Namespace:          request.Namespace,
	})
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError,
			fmt.Errorf("集群 %s 元数据查找失败，请稍后请重试: %w", request.ClusterName, err))
	}
	if clusterEntity == nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError,
			fmt.Errorf("集群 %s 不存在，请确认集群是否已部署: %w", request.ClusterName, err))
	}
	return clusterEntity, nil
}

// doHorizontalScaling 水平扩容具体实现
func (o *OpsRequestProvider) doHorizontalScaling(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateK8sClientError, err)
	}

	horizontalScaling, err := coreutil.CreateHorizontalScalingObject(request)
	if err != nil {
		return nil, err
	}

	// save opsRequest metadata
	if err = metautil.CreateOpsRequestMetaData(
		o.opsRequestProvider,
		o.clusterMetaProvider,
		request,
		horizontalScaling,
		ctx.RequestID,
		k8sClusterConfig.ID,
	); err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateMetaDataError, err)
	}

	if err = coreutil.CreateCRD(k8sClient, horizontalScaling); err != nil {
		return nil, fmt.Errorf("下发水平扩容任务失败: %w", err)
	}

	responseData, err := coreentity.GetOpsRequestData(horizontalScaling.ResourceObject)
	if err != nil {
		return nil, fmt.Errorf("获取水平扩容任务详情失败: %w", err)
	}
	return &responseData.Metadata, nil
}

// VolumeExpansion 磁盘扩容装饰方法
func (o *OpsRequestProvider) VolumeExpansion(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	clusterEntity, err := o.checkClusterExists(ctx, request)
	if err != nil {
		return nil, err
	}
	for _, component := range request.ComponentList {
		checkResult, err := addonopschecker.ComponentOpsChecker.Check(
			ctx,
			addonopschecker.AddonType(clusterEntity.AddonInfo.AddonType),
			addonopschecker.AddonComponent(component.ComponentName),
			addonopschecker.OperationType(ctx.RequestType),
			request,
		)
		if err != nil || !checkResult {
			return nil, err
		}
	}

	return o.withMetaDataSync(ctx, request, o.doVolumeExpansion, metautil.UpdateValWithCompList)
}

// doVolumeExpansion 磁盘扩容具体实现
func (o *OpsRequestProvider) doVolumeExpansion(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateK8sClientError, err)
	}

	clusterInfo, err := getClusterInfo(request, k8sClient)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetClusterError, err)
	}

	volumeExpansion, err := coreutil.CreateVolumeExpansionObject(request, clusterInfo)
	if err != nil {
		return nil, err
	}

	if err = metautil.CreateOpsRequestMetaData(
		o.opsRequestProvider,
		o.clusterMetaProvider,
		request,
		volumeExpansion,
		ctx.RequestID,
		k8sClusterConfig.ID,
	); err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateMetaDataError, err)
	}

	if err = coreutil.CreateCRD(k8sClient, volumeExpansion); err != nil {
		return nil, fmt.Errorf("下发磁盘扩容任务失败: %w", err)
	}

	responseData, err := coreentity.GetOpsRequestData(volumeExpansion.ResourceObject)
	if err != nil {
		return nil, fmt.Errorf("获取磁盘扩容任务详情失败: %w", err)
	}
	return &responseData.Metadata, nil
}

// StartCluster 启动集群装饰方法
func (o *OpsRequestProvider) StartCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	return o.withMetaDataSync(ctx, request, o.doStartCluster, nil)
}

// doStartCluster 启动集群
func (o *OpsRequestProvider) doStartCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateK8sClientError, err)
	}

	start, err := coreutil.CreateStartClusterObject(request)
	if err != nil {
		return nil, err
	}

	if err = metautil.CreateOpsRequestMetaData(
		o.opsRequestProvider,
		o.clusterMetaProvider,
		request,
		start,
		ctx.RequestID,
		k8sClusterConfig.ID,
	); err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateMetaDataError, err)
	}

	if err = coreutil.CreateCRD(k8sClient, start); err != nil {
		return nil, fmt.Errorf("下发集群启动任务失败: %w", err)
	}

	responseData, err := coreentity.GetOpsRequestData(start.ResourceObject)
	if err != nil {
		return nil, fmt.Errorf("获取集群启动任务详情失败: %w", err)
	}

	return &responseData.Metadata, nil
}

// RestartCluster 重启集群装饰方法
func (o *OpsRequestProvider) RestartCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	return o.withMetaDataSync(ctx, request, o.doRestartCluster, nil)
}

// RestartCluster 重启集群装饰方法
func (o *OpsRequestProvider) doRestartCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateK8sClientError, err)
	}

	if request.RestartList == nil {
		clusterResponseData, err := o.clusterProvider.DescribeCluster(request)
		if err != nil {
			return nil, errors.NewK8sDbsError(errors.DescribeClusterError, err)
		}
		request.RestartList = make([]opv1.ComponentOps, 0, len(clusterResponseData.Spec.ComponentList))
		for _, comp := range clusterResponseData.Spec.ComponentList {
			request.RestartList = append(request.RestartList, opv1.ComponentOps{ComponentName: comp.ComponentName})
		}
	}
	restart, err := coreutil.CreateRestartClusterObject(request)
	if err != nil {
		return nil, err
	}

	if err = metautil.CreateOpsRequestMetaData(
		o.opsRequestProvider,
		o.clusterMetaProvider,
		request,
		restart,
		ctx.RequestID,
		k8sClusterConfig.ID,
	); err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateMetaDataError, err)
	}

	if err = coreutil.CreateCRD(k8sClient, restart); err != nil {
		return nil, fmt.Errorf("下发集群重启任务失败: %w", err)
	}

	responseData, err := coreentity.GetOpsRequestData(restart.ResourceObject)
	if err != nil {
		return nil, fmt.Errorf("获取集群重启任务详情失败: %w", err)
	}
	return &responseData.Metadata, nil
}

// StopCluster 停止集群
func (o *OpsRequestProvider) StopCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	return o.withMetaDataSync(ctx, request, o.doStopCluster, nil)
}

// doStopCluster 停止集群
func (o *OpsRequestProvider) doStopCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateK8sClientError, err)
	}

	stop, err := coreutil.CreateStopClusterObject(request)
	if err != nil {
		return nil, err
	}

	if err = metautil.CreateOpsRequestMetaData(
		o.opsRequestProvider,
		o.clusterMetaProvider,
		request,
		stop,
		ctx.RequestID,
		k8sClusterConfig.ID,
	); err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateMetaDataError, err)
	}

	err = coreutil.CreateCRD(k8sClient, stop)
	if err != nil {
		return nil, fmt.Errorf("下发集群停止任务失败: %w", err)
	}

	responseData, err := coreentity.GetOpsRequestData(stop.ResourceObject)
	if err != nil {
		return nil, fmt.Errorf("获取集群停止任务详情失败: %w", err)
	}

	return &responseData.Metadata, nil
}

// UpgradeCluster 集群升级
func (o *OpsRequestProvider) UpgradeCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	return o.withMetaDataSync(ctx, request, o.doUpgradeCluster, metautil.UpdateValWithCompList)
}

// doUpgradeCluster 集群升级
func (o *OpsRequestProvider) doUpgradeCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateK8sClientError, err)
	}

	cluster, err := getClusterInfo(request, k8sClient)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetClusterError, err)
	}

	upgrade, err := coreutil.CreateUpgradeClusterObject(request, cluster)
	if err != nil {
		return nil, err
	}

	if err = metautil.CreateOpsRequestMetaData(
		o.opsRequestProvider,
		o.clusterMetaProvider,
		request,
		upgrade,
		ctx.RequestID,
		k8sClusterConfig.ID,
	); err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateMetaDataError, err)
	}

	err = coreutil.CreateCRD(k8sClient, upgrade)
	if err != nil {
		return nil, fmt.Errorf("下发集群升级任务失败: %w", err)
	}

	responseData, err := coreentity.GetOpsRequestData(upgrade.ResourceObject)
	if err != nil {
		return nil, fmt.Errorf("获取集群升级任务详情失败: %w", err)
	}
	return &responseData.Metadata, nil
}

// ExposeCluster 服务暴露
func (o *OpsRequestProvider) ExposeCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	return o.withMetaDataSync(ctx, request, o.doExposeCluster, nil)
}

// doExposeCluster 服务暴露
func (o *OpsRequestProvider) doExposeCluster(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
) (*coreentity.Metadata, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateK8sClientError, err)
	}

	expose, err := coreutil.CreateExposeClusterObject(request)
	if err != nil {
		return nil, err
	}

	if err = metautil.CreateOpsRequestMetaData(
		o.opsRequestProvider,
		o.clusterMetaProvider,
		request,
		expose,
		ctx.RequestID,
		k8sClusterConfig.ID,
	); err != nil {
		return nil, errors.NewK8sDbsError(errors.CreateMetaDataError, err)
	}

	if err = coreutil.CreateCRD(k8sClient, expose); err != nil {
		return nil, fmt.Errorf("下发服务暴露任务失败: %w", err)
	}

	responseData, err := coreentity.GetOpsRequestData(expose.ResourceObject)
	if err != nil {
		return nil, fmt.Errorf("获取服务暴露任务详情失败: %w", err)
	}
	return &responseData.Metadata, nil
}

// DescribeOpsRequest describe OpsRequest
func (o *OpsRequestProvider) DescribeOpsRequest(request *coreentity.Request) (*coreentity.OpsRequestData, error) {
	k8sClusterConfig, err := o.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)

	if err != nil {
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}
	crd := &coreentity.CustomResourceDefinition{
		ResourceName:         request.Metadata.OpsRequestName,
		Namespace:            request.Metadata.Namespace,
		GroupVersionResource: kbtypes.OpsGVR(),
	}
	opsRequest, err := coreutil.GetCRD(k8sClient, crd)
	if err != nil {
		return nil, err
	}

	responseData, err := coreentity.GetOpsRequestData(opsRequest)
	if err != nil {
		return nil, err
	}
	return responseData, nil
}

// validateProvider 验证 OpsRequestProvider 必要字段
func (o *OpsRequestProvider) validateProvider() error {
	if o.opsRequestProvider == nil {
		return fmt.Errorf("missing opsRequestProvider")
	}
	if o.clusterMetaProvider == nil {
		return fmt.Errorf("missing clusterMetaProvider")
	}
	if o.releaseMetaProvider == nil {
		return fmt.Errorf("missing releaseMetaProvider")
	}
	if o.reqRecordProvider == nil {
		return fmt.Errorf("missing reqRecordProvider")
	}
	if o.clusterConfigProvider == nil {
		return fmt.Errorf("missing clusterConfigProvider")
	}
	return nil
}

// getClusterInfo Query cluster information and return
func getClusterInfo(request *coreentity.Request, k8sClient *commutil.K8sClient) (*kbv1.Cluster, error) {
	// Construct and query crd resources
	crd := &coreentity.CustomResourceDefinition{
		ResourceName:         request.Metadata.ClusterName,
		Namespace:            request.Metadata.Namespace,
		GroupVersionResource: kbtypes.ClusterGVR(),
	}
	clusterCR, err := coreutil.GetCRD(k8sClient, crd)
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
