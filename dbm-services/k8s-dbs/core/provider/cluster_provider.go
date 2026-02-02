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
	commentity "k8s-dbs/common/entity"
	commutil "k8s-dbs/common/util"
	addonopschecker "k8s-dbs/core/checker/addonoperation"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	coreutil "k8s-dbs/core/util"
	infrautil "k8s-dbs/infrastructure/util"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	metautil "k8s-dbs/metadata/util"
	"log/slog"
	"os"
	"sort"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"

	kbappv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	kbworkloadv1 "github.com/apecloud/kubeblocks/apis/workloads/v1alpha1"
	"helm.sh/helm/v3/pkg/action"
	"helm.sh/helm/v3/pkg/chart/loader"
	helmcli "helm.sh/helm/v3/pkg/cli"

	dbserrors "k8s-dbs/errors"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	"github.com/pkg/errors"
	"github.com/samber/lo"

	"k8s-dbs/infrastructure/thirdapi"
)

// ClusterProvider 集群管理核心服务
type ClusterProvider struct {
	addonMetaProvider       metaprovider.K8sCrdStorageAddonProvider
	clusterMetaProvider     metaprovider.K8sCrdClusterProvider
	componentMetaProvider   metaprovider.K8sCrdComponentProvider
	clusterConfigProvider   metaprovider.K8sClusterConfigProvider
	reqRecordProvider       metaprovider.ClusterRequestRecordProvider
	releaseMetaProvider     metaprovider.AddonClusterReleaseProvider
	clusterHelmRepoProvider metaprovider.AddonClusterHelmRepoProvider
	ClusterTagProvider      metaprovider.K8sCrdClusterTagProvider
	dbmAPIService           *thirdapi.DbmAPIService
}

// ClusterProviderOptions ClusterProvider 的函数选项
type ClusterProviderOptions func(*ClusterProvider)

// ClusterProviderBuilder 辅助构建 ClusterProvider
type ClusterProviderBuilder struct{}

// WithClusterMeta 设置 ClusterMetaProvider
func (c *ClusterProviderBuilder) WithClusterMeta(
	p metaprovider.K8sCrdClusterProvider,
) ClusterProviderOptions {
	return func(c *ClusterProvider) {
		c.clusterMetaProvider = p
	}
}

// WithComponentMeta 设置 ComponentMetaProvider
func (c *ClusterProviderBuilder) WithComponentMeta(
	p metaprovider.K8sCrdComponentProvider,
) ClusterProviderOptions {
	return func(c *ClusterProvider) {
		c.componentMetaProvider = p
	}
}

// WithClusterConfigMeta 设置 ClusterConfigMetaProvider
func (c *ClusterProviderBuilder) WithClusterConfigMeta(
	p metaprovider.K8sClusterConfigProvider,
) ClusterProviderOptions {
	return func(c *ClusterProvider) {
		c.clusterConfigProvider = p
	}
}

// WithReqRecordMeta 设置 ReqRecordProvider
func (c *ClusterProviderBuilder) WithReqRecordMeta(
	p metaprovider.ClusterRequestRecordProvider,
) ClusterProviderOptions {
	return func(c *ClusterProvider) {
		c.reqRecordProvider = p
	}
}

// WithReleaseMeta 设置 ReleaseMetaProvider
func (c *ClusterProviderBuilder) WithReleaseMeta(
	p metaprovider.AddonClusterReleaseProvider,
) ClusterProviderOptions {
	return func(c *ClusterProvider) {
		c.releaseMetaProvider = p
	}
}

// WithClusterHelmRepoMeta 设置 ClusterProviderBuilder
func (c *ClusterProviderBuilder) WithClusterHelmRepoMeta(
	p metaprovider.AddonClusterHelmRepoProvider,
) ClusterProviderOptions {
	return func(c *ClusterProvider) {
		c.clusterHelmRepoProvider = p
	}
}

// WithAddonMeta 设置 AddonMetaProvider
func (c *ClusterProviderBuilder) WithAddonMeta(
	p metaprovider.K8sCrdStorageAddonProvider,
) ClusterProviderOptions {
	return func(c *ClusterProvider) {
		c.addonMetaProvider = p
	}
}

// WithClusterTagsMeta 设置 ClusterTagProvider
func (c *ClusterProviderBuilder) WithClusterTagsMeta(
	p metaprovider.K8sCrdClusterTagProvider,
) ClusterProviderOptions {
	return func(c *ClusterProvider) {
		c.ClusterTagProvider = p
	}
}

// WithDbmAPIService 设置 DbmAPIService
func (c *ClusterProviderBuilder) WithDbmAPIService(
	service *thirdapi.DbmAPIService,
) ClusterProviderOptions {
	return func(c *ClusterProvider) {
		c.dbmAPIService = service
	}
}

// validateProvider 验证 ClusterProvider 必要字段
func (c *ClusterProvider) validateProvider() error {
	if c.clusterMetaProvider == nil {
		return errors.New("clusterMetaProvider is required")
	}
	if c.componentMetaProvider == nil {
		return errors.New("componentMetaProvider is required")
	}
	if c.clusterConfigProvider == nil {
		return errors.New("clusterConfigProvider is required")
	}
	if c.reqRecordProvider == nil {
		return errors.New("reqRecordProvider is required")
	}
	if c.releaseMetaProvider == nil {
		return errors.New("releaseMetaProvider is required")
	}
	if c.clusterHelmRepoProvider == nil {
		return errors.New("clusterHelmRepoProvider is required")
	}
	if c.addonMetaProvider == nil {
		return errors.New("addonMetaProvider is required")
	}
	if c.ClusterTagProvider == nil {
		return errors.New("ClusterTagProvider is required")
	}
	// 新增dbmAPIService验证
	if c.dbmAPIService == nil {
		return errors.New("dbmAPIService is required")
	}
	return nil
}

// NewClusterProvider 创建 ClusterProvider 实例
func NewClusterProvider(option ...ClusterProviderOptions) (*ClusterProvider, error) {
	provider := &ClusterProvider{}
	for _, opt := range option {
		opt(provider)
	}
	if err := provider.validateProvider(); err != nil {
		slog.Error("failed to validate cluster provider", "error", err)
		return nil, err
	}
	return provider, nil
}

// InstanceSetGVR returns the GroupVersionResource definition for InstanceSet custom resource.
// InstanceSetGVR() is missing in kbcli v0.9.3, so it needs to be supplemented locally
func InstanceSetGVR() schema.GroupVersionResource {
	return schema.GroupVersionResource{
		Group:    "workloads.kubeblocks.io",
		Version:  "v1alpha1",
		Resource: "instancesets",
	}
}

// CreateCluster 创建集群
func (c *ClusterProvider) CreateCluster(ctx *commentity.DbsContext, request *coreentity.Request) error {
	// 检查集群版本
	if err := c.checkClusterVersion(request, dbserrors.CreateClusterError); err != nil {
		return err
	}
	// 检查是否重复创建
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}
	originClusterEntity, err := c.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		K8sClusterConfigID: k8sClusterConfig.ID,
		ClusterName:        request.ClusterName,
		Namespace:          request.Namespace,
	})
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}
	if originClusterEntity != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateClusterError,
			fmt.Errorf("集群 %s 已存在，请勿重复创建", request.ClusterName))
	}
	// 设置默认删除策略为 Delete
	if request.TerminationPolicy == "" {
		request.TerminationPolicy = coreconst.Delete
	}
	// 保存审计日志
	addedRequestEntity, err := metautil.SaveAuditLog(c.reqRecordProvider, request, ctx.RequestType)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateK8sClientError, err)
	}
	// 安装集群
	values, err := c.installHelmRelease(request, k8sClient)
	if err != nil {
		exists, checkErr := coreutil.CheckClusterReleaseExists(k8sClient, request.Namespace, request.ClusterName)
		if checkErr != nil {
			return dbserrors.NewK8sDbsError(dbserrors.GetClusterError,
				fmt.Errorf("检索集群 release 失败: %w", err))
		}
		if exists {
			uninstallErr := coreutil.UninstallClusterRelease(k8sClient, request.Namespace,
				request.ClusterName, metav1.DeletePropagationBackground)
			if uninstallErr != nil {
				return dbserrors.NewK8sDbsError(dbserrors.DeleteClusterError,
					fmt.Errorf("卸载集群 release 失败: %w", uninstallErr))
			}
		}
		return dbserrors.NewK8sDbsError(dbserrors.CreateClusterError, err)
	}
	// 保存集群元数据
	clusterEntity, err := c.saveClusterCRMetaData(request, addedRequestEntity.RequestID, k8sClusterConfig.ID)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateMetaDataError, err)
	}
	// 保存集群标签元数据
	if len(request.Tags) > 0 {
		if err = c.saveClusterTagsMeta(request, clusterEntity); err != nil {
			return dbserrors.NewK8sDbsError(dbserrors.CreateMetaDataError, err)
		}
	}
	// 保存集群 release 元数据
	if err = c.saveClusterReleaseMeta(request, k8sClusterConfig, values); err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateMetaDataError, err)
	}
	// 检查环境变量ASYNC_TO_DBM，控制是否启用异步处理
	asyncToDBM := os.Getenv(coreconst.AsyncToDBMEnv)
	if asyncToDBM == coreconst.AsyncToDBMEnabled {
		infrautil.AsyncClusterCreated(clusterEntity, c.dbmAPIService)
	}
	return nil
}

// checkClusterVersion 检查集群版本是否与存储插件的支持版本匹配
// 参数:
//
//	request - 包含集群配置信息的请求对象
//	errCode - 当前操作的错误码（创建/更新等）
//	err - 可能的错误信息
//
// 返回值:
//
//	error - 检查过程中遇到的错误，如果检查通过则为nil
//	bool - 是否发生了错误，true表示有错误发生
func (c *ClusterProvider) checkClusterVersion(request *coreentity.Request, errCode dbserrors.ErrorCode) error {
	addonQueryParams := &metaentity.AddonQueryParams{
		AddonType:    request.StorageAddonType,
		AddonVersion: request.StorageAddonVersion,
	}
	storageAddon, err := c.addonMetaProvider.FindStorageAddonByParams(addonQueryParams)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError,
			fmt.Errorf("查询存储插件元数据失败: %w", err))
	}
	if len(storageAddon) == 0 {
		return dbserrors.NewK8sDbsError(errCode,
			fmt.Errorf("插件类型 '%s' 版本 '%s' 不存在或未配置，请检查插件配置", request.StorageAddonType, request.StorageAddonVersion))
	}

	// 反序列化支持的版本列表
	var supportedVersions []string
	if err := json.Unmarshal([]byte(storageAddon[0].SupportedVersions), &supportedVersions); err != nil {
		slog.Error("failed to unmarshal supported versions", "error", err)
		return dbserrors.NewK8sDbsError(errCode,
			fmt.Errorf("supported versions 反序列化失败"))
	}

	// 检查组件版本是否在支持的版本列表中
	for _, component := range request.ComponentList {
		if component.Version == nil {
			continue
		}
		if !lo.Contains(supportedVersions, *component.Version) {
			return dbserrors.NewK8sDbsError(errCode,
				fmt.Errorf("组件 %s 的版本 %s 不在支持的版本列表中，支持的版本: %v",
					component.ComponentName, *component.Version, supportedVersions))
		}
	}

	// 反序列化支持的AC版本列表
	var supportedAcVersions []string
	if err := json.Unmarshal([]byte(storageAddon[0].SupportedAcVersions), &supportedAcVersions); err != nil {
		slog.Error("failed to unmarshal supported ac versions", "error", err)
		return dbserrors.NewK8sDbsError(errCode,
			fmt.Errorf("supported ac versions 反序列化失败"))
	}

	if !lo.Contains(supportedAcVersions, request.AddonClusterVersion) {
		return dbserrors.NewK8sDbsError(errCode,
			fmt.Errorf("addonClusterVersion 版本 %s 不在支持的版本列表中，支持的版本: %v",
				request.AddonClusterVersion, supportedAcVersions))
	}
	return nil
}

// saveClusterReleaseMeta 记录集群 release 元数据
func (c *ClusterProvider) saveClusterReleaseMeta(
	request *coreentity.Request,
	k8sClusterConfig *metaentity.K8sClusterConfigEntity,
	values map[string]interface{},
) error {
	clusterRelease, err := buildClusterReleaseEntity(
		k8sClusterConfig.ID,
		request,
		coreconst.DefaultRepoName,
		coreconst.DefaultRepoRepository,
		values,
	)
	if err != nil {
		slog.Error("build cluster release entity error", "error", err.Error())
		return fmt.Errorf("failed to build cluster release entity: %w", err)
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

// saveClusterMetaData 记录集群 tags
func (c *ClusterProvider) saveClusterTagsMeta(
	request *coreentity.Request,
	cluster *metaentity.K8sCrdClusterEntity,
) error {
	if len(request.Tags) == 0 {
		return nil
	}
	var tagEntities []*metaentity.K8sCrdClusterTagEntity
	for _, tag := range request.Tags {
		tagEntity := &metaentity.K8sCrdClusterTagEntity{
			CrdClusterID: cluster.ID,
			ClusterTag:   tag,
		}
		tagEntities = append(tagEntities, tagEntity)
	}
	dbsCtx := &commentity.DbsContext{
		BkAuth: &request.BKAuth,
	}
	_, err := c.ClusterTagProvider.BatchCreate(dbsCtx, tagEntities)
	if err != nil {
		return err
	}
	return nil
}

// saveClusterMetaData 记录集群关联资源元数据
func (c *ClusterProvider) saveClusterCRMetaData(
	request *coreentity.Request,
	requestID string,
	k8sClusterConfigID uint64,
) (*metaentity.K8sCrdClusterEntity, error) {
	// 记录 cluster 元数据
	addedClusterEntity, err := c.saveClusterMeta(request, requestID, k8sClusterConfigID)
	if err != nil {
		return nil, err
	}

	clusterID := addedClusterEntity.ID
	// 记录 component 元数据
	_, err = c.saveComponentMeta(request, clusterID)
	if err != nil {
		return nil, err
	}
	return addedClusterEntity, nil
}

// UpdateClusterRelease 更新（或局部更新）集群 Release
// isPartial 表示是否为局部更新，true 表示局部更新，false 表示全量更新
func (c *ClusterProvider) UpdateClusterRelease(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
	isPartial bool,
) error {
	_, err := metautil.SaveAuditLog(c.reqRecordProvider, request, ctx.RequestType)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateMetaDataError, err)
	}
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}
	ctx.K8sClusterConfigID = k8sClusterConfig.ID
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateK8sClientError, err)
	}
	clusterEntity, err := c.fillClusterMetaInfo(k8sClusterConfig.ID, request)
	if err != nil {
		return err
	}
	// 检查 addonClusterVersion 是否在支持的版本列表中
	if err := c.validateAddonClusterVersion(request, clusterEntity); err != nil {
		return err
	}
	// 检查集群版本
	if err := c.checkClusterVersion(request, dbserrors.UpdateClusterError); err != nil {
		return err
	}

	// 更新 cluster release
	values, err := c.updateClusterRelease(ctx, request, k8sClient, isPartial)
	if err != nil {
		slog.Error("failed to update cluster", "error", err)
		return dbserrors.NewK8sDbsError(dbserrors.UpdateClusterError, err)
	}
	if err = c.updateReleaseMeta(values, k8sClusterConfig, request); err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.UpdateMetaDataError, err)
	}
	// 更新集群 cluster 元数据
	updatedClusterEntity, err := metautil.UpdateClusterMeta(c.clusterMetaProvider, ctx, request)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.UpdateMetaDataError, err)
	}

	// 检查环境变量ASYNC_TO_DBM，控制是否启用异步处理
	asyncToDBM := os.Getenv(coreconst.AsyncToDBMEnv)
	if asyncToDBM == coreconst.AsyncToDBMEnabled {
		infrautil.AsyncClusterUpdated(updatedClusterEntity, c.dbmAPIService)
	}

	return nil
}

// fillClusterMetaInfo 补全 cluster 元信息
func (c *ClusterProvider) fillClusterMetaInfo(
	k8sClusterConfigID uint64,
	request *coreentity.Request,
) (*metaentity.K8sCrdClusterEntity, error) {
	// check cluster
	clusterEntity, err := c.clusterMetaProvider.FindByParams(&metaentity.ClusterQueryParams{
		K8sClusterConfigID: k8sClusterConfigID,
		ClusterName:        request.ClusterName,
		Namespace:          request.Namespace,
	})
	if err != nil {
		return nil, dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}
	if clusterEntity == nil {
		return nil, dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError,
			fmt.Errorf("集群 %s 元数据不存在，操作失败", request.ClusterName))
	}
	if request.AddonClusterVersion == "" {
		request.AddonClusterVersion = clusterEntity.AddonClusterVersion
	}
	request.StorageAddonType = clusterEntity.AddonInfo.AddonType
	request.StorageAddonVersion = clusterEntity.AddonInfo.AddonVersion
	return clusterEntity, nil
}

// updateReleaseMeta 更新 release meta 元数据
func (c *ClusterProvider) updateReleaseMeta(
	values map[string]interface{},
	k8sClusterConfig *metaentity.K8sClusterConfigEntity,
	request *coreentity.Request,
) error {
	jsonData, err := json.Marshal(values)
	if err != nil {
		return err
	}
	releaseEntity, err := c.releaseMetaProvider.FindByParams(
		&metaentity.ClusterReleaseQueryParams{
			K8sClusterConfigID: k8sClusterConfig.ID,
			ReleaseName:        request.ClusterName,
			Namespace:          request.Namespace,
		})
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}
	releaseEntity.ChartValues = string(jsonData)
	_, err = c.releaseMetaProvider.UpdateClusterRelease(releaseEntity)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.UpdateMetaDataError, err)
	}
	return nil
}

// DeleteCluster 删除集群
func (c *ClusterProvider) DeleteCluster(ctx *commentity.DbsContext, request *coreentity.Request) error {
	_, err := metautil.SaveAuditLog(c.reqRecordProvider, request, ctx.RequestType)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateMetaDataError, err)
	}
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateK8sClientError, err)
	}
	clusterEntity, err := metautil.GetClusterMeta(c.clusterMetaProvider, request, k8sClusterConfig)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}

	// 集群操作检查
	ctx.ClusterEntity = clusterEntity
	checkResult, err := addonopschecker.ClusterOpsChecker.Check(
		ctx,
		addonopschecker.AddonType(clusterEntity.AddonInfo.AddonType),
		addonopschecker.OperationType(ctx.RequestType),
		request,
	)
	if err != nil || !checkResult {
		return err
	}
	// 清理元数据
	if err := c.clearClusterRelateMeta(ctx, clusterEntity); err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteMetaDataError,
			fmt.Errorf("清理 cluster 元数据失败: %w", err))
	}

	// 删除集群
	if err = coreutil.UninstallClusterRelease(k8sClient, request.Namespace,
		request.ClusterName, metav1.DeletePropagationBackground); err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteClusterError,
			fmt.Errorf("删除集群 release 失败: %w", err))
	}

	// 检查环境变量ASYNC_TO_DBM，控制是否启用异步处理
	asyncToDBM := os.Getenv(coreconst.AsyncToDBMEnv)
	if asyncToDBM == coreconst.AsyncToDBMEnabled {
		infrautil.AsyncClusterDeleted(clusterEntity, c.dbmAPIService)
	}

	return nil
}

// clearClusterRelateMeta 清理 cluster 关联的元数据信息
func (c *ClusterProvider) clearClusterRelateMeta(
	ctx *commentity.DbsContext,
	clusterEntity *metaentity.K8sCrdClusterEntity,
) error {
	// 清理 cluster 关联资源元数据
	if err := c.clearClusterCRMetaData(ctx, clusterEntity); err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteClusterError, err)
	}

	// 清理 cluster tag 元数据
	if err := c.clearClusterTagsMeta(ctx, clusterEntity); err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteClusterError, err)
	}

	// 清理 cluster release 元数据
	if err := c.clearClusterReleaseMeta(ctx, clusterEntity); err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteClusterError, err)
	}
	return nil
}

// clearClusterReleaseMeta 清理 cluster release 元数据
func (c *ClusterProvider) clearClusterReleaseMeta(
	_ *commentity.DbsContext,
	clusterEntity *metaentity.K8sCrdClusterEntity,
) error {
	releaseEntity, err := c.releaseMetaProvider.FindByParams(
		&metaentity.ClusterReleaseQueryParams{
			K8sClusterConfigID: clusterEntity.K8sClusterConfigID,
			ReleaseName:        clusterEntity.ClusterName,
			Namespace:          clusterEntity.Namespace,
		})
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}
	_, err = c.releaseMetaProvider.DeleteClusterReleaseByID(releaseEntity.ID)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteClusterError, err)
	}
	return nil
}

// clearClusterTagsMeta 清理 cluster tag 元数据
func (c *ClusterProvider) clearClusterTagsMeta(
	ctx *commentity.DbsContext,
	clusterEntity *metaentity.K8sCrdClusterEntity,
) error {
	_, err := c.ClusterTagProvider.DeleteByClusterID(ctx, clusterEntity.ID)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteClusterError, err)
	}
	return nil
}

// clearClusterCRMetaData 清理 cluster 关联的资源元数据
func (c *ClusterProvider) clearClusterCRMetaData(
	_ *commentity.DbsContext,
	clusterEntity *metaentity.K8sCrdClusterEntity,
) error {
	_, err := c.clusterMetaProvider.DeleteClusterByID(clusterEntity.ID)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteClusterError, err)
	}
	_, err = c.componentMetaProvider.DeleteComponentByClusterID(clusterEntity.ID)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.DeleteClusterError, err)
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

// saveClusterMeta Save and return the cluster instance
func (c *ClusterProvider) saveClusterMeta(
	request *coreentity.Request,
	requestID string,
	k8sClusterConfigID uint64,
) (*metaentity.K8sCrdClusterEntity, error) {
	addonQueryParams := &metaentity.AddonQueryParams{
		AddonType:    request.StorageAddonType,
		AddonVersion: request.StorageAddonVersion,
	}
	storageAddon, err := c.addonMetaProvider.FindStorageAddonByParams(addonQueryParams)
	if err != nil {
		slog.Error("failed to get storage addon", "error", err)
		return nil, err
	}
	if len(storageAddon) != 1 {
		errMsg := fmt.Sprintf("expected 1 storage addon, found %d", len(storageAddon))
		slog.Error("failed to get storage addon", "error", errMsg)
		return nil, err
	}
	serviceVersion, err := coreutil.SVRFactory.
		GetResolver(coreconst.StorageAddonType(request.StorageAddonType)).
		Resolve(request.ComponentList)
	if err != nil {
		slog.Error("failed to get serviceVersion", "error", err)
		return nil, err
	}

	clusterEntity := &metaentity.K8sCrdClusterEntity{
		AddonID:             storageAddon[0].ID,
		AddonClusterVersion: request.AddonClusterVersion,
		ServiceVersion:      serviceVersion,
		TopoName:            request.TopoName,
		TerminationPolicy:   request.TerminationPolicy,
		ClusterName:         request.ClusterName,
		ClusterAlias:        request.ClusterAlias,
		Namespace:           request.Namespace,
		RequestID:           requestID,
		K8sClusterConfigID:  k8sClusterConfigID,
		BkBizID:             request.BkBizID,
		BkBizName:           request.BkBizName,
		BkAppAbbr:           request.BkAppAbbr,
		BkAppCode:           request.BKAuth.BkAppCode,
		Description:         request.Description,
		CreatedBy:           request.BKAuth.BkUserName,
		UpdatedBy:           request.BKAuth.BkUserName,
	}
	addedClusterEntity, err := c.clusterMetaProvider.CreateCluster(clusterEntity)
	if err != nil {
		slog.Error("failed to create cluster entity", "error", err)
		return nil, err
	}
	addedClusterEntity.AddonInfo = storageAddon[0]
	return addedClusterEntity, nil
}

// saveComponentMeta Save and return an array of component instances
func (c *ClusterProvider) saveComponentMeta(
	request *coreentity.Request,
	crdClusterID uint64,
) ([]*metaentity.K8sCrdComponentEntity, error) {
	var compEntityList []*metaentity.K8sCrdComponentEntity
	for _, comp := range request.ComponentList {
		compName := request.Metadata.ClusterName + "-" + comp.ComponentName
		componentEntity := &metaentity.K8sCrdComponentEntity{
			ComponentName: compName,
			CrdClusterID:  crdClusterID,
			CreatedBy:     request.BKAuth.BkUserName,
			UpdatedBy:     request.BKAuth.BkUserName,
		}
		_, err := c.componentMetaProvider.CreateComponent(componentEntity)
		if err != nil {
			return nil, fmt.Errorf("failed to create component entity %s : %w", compName, err)
		}
		compEntityList = append(compEntityList, componentEntity)
	}
	return compEntityList, nil
}

// getClusterDataResp Get cluster details
func (c *ClusterProvider) getClusterDataResp(request *coreentity.Request) (*coreentity.ClusterResponseData, error) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)

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
	repoName string,
	repoRepository string,
	releaseValues map[string]interface{},
) (*metaentity.AddonClusterReleaseEntity, error) {
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

	return &metaentity.AddonClusterReleaseEntity{
		K8sClusterConfigID: k8sClusterConfigID,
		ReleaseName:        releaseName,
		Namespace:          namespace,
		ChartName:          chartName,
		ChartVersion:       chartVersion,
		RepoName:           repoName,
		RepoRepository:     repoRepository,
		ChartValues:        jsonStr,
		CreatedBy:          request.BKAuth.BkUserName,
		UpdatedBy:          request.BKAuth.BkUserName,
	}, nil
}

// installHelmRelease 安装 chart
func (c *ClusterProvider) installHelmRelease(
	request *coreentity.Request,
	k8sClient *commutil.K8sClient,
) (map[string]interface{}, error) {
	actionConfig, err := coreutil.BuildHelmActionConfig(request.Namespace, k8sClient)
	if err != nil {
		slog.Error("获取集群配置信息失败", "error", err)
		return nil, errors.Wrapf(err, "获取集群 %s 配置信息失败", request.K8sClusterName)
	}

	helmRepo, err := c.getClusterHelmRepository(request)
	if err != nil {
		return nil, errors.Wrapf(err, "获取集群存储 %s 的 Helm 仓库信息失败", request.StorageAddonType)
	}
	if helmRepo == nil {
		return nil, fmt.Errorf("集群 %s 的 Helm 仓库信息为空，请检查插件类型 %s 版本 %s 的仓库配置",
			request.ClusterName, request.StorageAddonType, request.AddonClusterVersion)
	}

	addonClusterVersion := request.AddonClusterVersion
	if addonClusterVersion == "" {
		addonClusterVersion = request.StorageAddonVersion
	}
	install := action.NewInstall(actionConfig)
	install.ReleaseName = request.ClusterName
	install.Namespace = request.Namespace
	install.RepoURL = helmRepo.RepoRepository
	install.Version = addonClusterVersion
	install.Timeout = coreconst.HelmOperationTimeout
	install.CreateNamespace = true
	install.Wait = true
	install.Username = helmRepo.RepoUsername
	install.Password = helmRepo.RepoPassword
	chartRequested, err := install.ChartPathOptions.LocateChart(request.StorageAddonType+"-cluster", helmcli.New())
	if err != nil {
		slog.Error("failed to locate helm chart requested", "error", err)
		return nil, fmt.Errorf("failed to locate helm chart requested\n%s", err)
	}
	chart, err := loader.Load(chartRequested)
	if err != nil {
		slog.Error("failed to load helm chart requested", "error", err)
		return nil, fmt.Errorf("failed to load helm chart requested\n%s", err)
	}
	values := chart.Values
	err = coreutil.MergeValues(values, request, true)
	if err != nil {
		slog.Error("failed to merge dynamic values", "error", err)
		return nil, fmt.Errorf("failed to merge dynamic values  %w", err)
	}
	_, err = install.Run(chart, values)
	if err != nil {
		slog.Error("cluster install failed", "clusterName", request.ClusterName, "error", err)
		return nil, dbserrors.NewK8sDbsError(dbserrors.InstallHelmChartErr,
			fmt.Errorf("failed to install cluster %s: %w", request.ClusterName, err))
	}
	return values, nil
}

// updateClusterRelease 更新 cluster release
func (c *ClusterProvider) updateClusterRelease(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
	k8sClient *commutil.K8sClient,
	isPartial bool,
) (map[string]interface{}, error) {
	actionConfig, err := coreutil.BuildHelmActionConfig(request.Namespace, k8sClient)
	if err != nil {
		slog.Error("failed to build helm action config", "error", err)
		return nil, err
	}
	values, err := c.doUpdateClusterRelease(ctx, request, actionConfig, isPartial)
	if err != nil {
		slog.Error("cluster update failed", "clusterName", request.ClusterName, "error", err)
		return nil, err
	}
	return values, nil
}

// doUpdateClusterRelease 执行更新 release
func (c *ClusterProvider) doUpdateClusterRelease(
	ctx *commentity.DbsContext,
	request *coreentity.Request,
	actionConfig *action.Configuration,
	isPartial bool,
) (map[string]interface{}, error) {
	helmRepo, err := c.getClusterHelmRepository(request)
	if err != nil {
		slog.Error("failed to get helm repo", "error", err)
		return nil, err
	}
	if helmRepo == nil {
		return nil, fmt.Errorf("集群 %s 的 Helm 仓库信息为空，请检查插件类型 %s 版本 %s 的仓库配置",
			request.ClusterName, request.StorageAddonType, request.AddonClusterVersion)
	}
	upgrade := action.NewUpgrade(actionConfig)
	upgrade.Namespace = request.Namespace
	upgrade.RepoURL = helmRepo.RepoRepository
	upgrade.Version = request.AddonClusterVersion
	upgrade.Timeout = coreconst.HelmOperationTimeout
	upgrade.Wait = true
	upgrade.Username = helmRepo.RepoUsername
	upgrade.Password = helmRepo.RepoPassword

	chartRequested, err := upgrade.ChartPathOptions.LocateChart(request.StorageAddonType+"-cluster", helmcli.New())
	if err != nil {
		slog.Error("failed to locate helm chart requested", "error", err)
		return nil, err
	}

	chart, err := loader.Load(chartRequested)
	if err != nil {
		slog.Error("failed to load helm chart requested", "error", err)
		return nil, err
	}

	var values map[string]interface{}
	if isPartial {
		// 这里改为从 release 元数据表中获取最新的 values 配置
		releaseEntity, err := c.releaseMetaProvider.FindByParams(&metaentity.ClusterReleaseQueryParams{
			Namespace:          request.Namespace,
			ReleaseName:        request.ClusterName,
			K8sClusterConfigID: ctx.K8sClusterConfigID,
		})
		if err != nil {
			return nil, dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError,
				fmt.Errorf("获取集群 release 元数据失败 %w", err))
		}
		var currentValues map[string]any
		err = json.Unmarshal([]byte(releaseEntity.ChartValues), &currentValues)
		if err != nil {
			return nil, err
		}
		if err = coreutil.MergeValues(currentValues, request, false); err != nil {
			return nil, err
		}
		values = currentValues
	} else {
		chartValues := chart.Values
		err = coreutil.MergeValues(chartValues, request, false)
		if err != nil {
			return nil, err
		}
		values = chartValues
	}
	_, err = upgrade.Run(request.ClusterName, chart, values)
	if err != nil {
		slog.Error("cluster update failed", "clusterName", request.ClusterName, "error", err)
		return nil, err
	}
	return values, nil
}

// getClusterHelmRepository 获取 cluster helm repository
func (c *ClusterProvider) getClusterHelmRepository(
	request *coreentity.Request,
) (*metaentity.AddonClusterHelmRepoEntity, error) {
	addonClusterVersion := lo.Ternary(request.AddonClusterVersion == "",
		request.StorageAddonVersion, request.AddonClusterVersion)
	repoParams := &metaentity.HelmRepoQueryParams{
		ChartName:    request.StorageAddonType + "-cluster",
		ChartVersion: addonClusterVersion,
	}
	helmRepo, err := c.clusterHelmRepoProvider.FindByParams(repoParams)
	if err != nil {
		slog.Error("failed to find helm repo for cluster", "clusterName", request.ClusterName, "error", err)
		return nil, err
	}
	return helmRepo, nil
}

// GetClusterEvent 	获取 cluster 运行事件
func (c *ClusterProvider) GetClusterEvent(request *coreentity.Request) (*corev1.EventList, error) {
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		slog.Error("failed to get k8sClusterConfig", "error", err)
		return nil, fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		slog.Error("failed to create k8sClient", "error", err)
		return nil, fmt.Errorf("failed to create k8sClient: %w", err)
	}

	// Retrieve the cluster object using dynamic client
	cluster, err := k8sClient.DynamicClient.
		Resource(kbtypes.ClusterGVR()).
		Namespace(request.Namespace).
		Get(context.TODO(), request.ClusterName, metav1.GetOptions{})
	if err != nil {
		slog.Error("failed to get cluster object", "error", err)
		return nil, fmt.Errorf("failed to get cluster object: %w", err)
	}

	var data *kbappv1.Cluster
	err = runtime.DefaultUnstructuredConverter.FromUnstructured(cluster.Object, &data)
	if err != nil {
		slog.Error("failed to convert unstructured data", "error", err)
		return nil, fmt.Errorf("failed to convert unstructured data: %w", err)
	}

	// Retrieve events using CoreV1 API with the constructed field selector
	clusterEvents, err := k8sClient.ClientSet.CoreV1().
		Events(request.Namespace).
		List(context.Background(), metav1.ListOptions{
			FieldSelector: fmt.Sprintf("involvedObject.uid=%s", string(cluster.GetUID())),
		})
	if err != nil {
		slog.Error("failed to list events for cluster", "error", err)
		return nil, fmt.Errorf("failed to list events for cluster %s: %w", request.ClusterName, err)
	}

	// Query all associated InstanceSet events
	instanceSetEvents, err := c.getInstanceSetEvents(k8sClient, request.Namespace, request.ClusterName)
	if err != nil {
		slog.Error("failed to list events for instanceSet", "error", err)
		return nil, fmt.Errorf("failed to list events for instanceSet: %w", err)
	}

	// Merge Cluster and InstanceSet events and sort them by time
	allEvents := mergeAndSortEvents(clusterEvents, instanceSetEvents)
	return allEvents, nil
}

// getInstanceSetEvents 查询与 Cluster 关联的所有 InstanceSet 事件
func (c *ClusterProvider) getInstanceSetEvents(k8sClient *commutil.K8sClient, namespace, clusterName string) (
	*corev1.EventList, error) {
	crd := &coreentity.CustomResourceDefinition{
		GroupVersionResource: InstanceSetGVR(),
		Namespace:            namespace,
		Labels: map[string]string{
			coreconst.InstanceName: clusterName,
		},
	}

	instanceSetList, err := coreutil.ListCRD(k8sClient, crd)
	if err != nil {
		slog.Error("failed to list InstanceSets", "error", err)
		return nil, fmt.Errorf("failed to list InstanceSets: %w", err)
	}

	var allInstanceSetEvents []corev1.Event
	for _, item := range instanceSetList.Items {
		var instanceSet *kbworkloadv1.InstanceSet
		if err := runtime.DefaultUnstructuredConverter.FromUnstructured(item.Object, &instanceSet); err != nil {
			slog.Error("failed to convert InstanceSet", "error", err)
			return nil, fmt.Errorf("failed to convert InstanceSet: %w", err)
		}

		events, err := k8sClient.ClientSet.CoreV1().Events(namespace).List(context.Background(), metav1.ListOptions{
			FieldSelector: fmt.Sprintf("involvedObject.uid=%s", string(instanceSet.GetUID())),
		})
		if err != nil {
			slog.Error("failed to list InstanceSet events", "uid", instanceSet.UID, "error", err)
			return nil, fmt.Errorf("failed to list InstanceSet events: %w", err)
		}
		allInstanceSetEvents = append(allInstanceSetEvents, events.Items...)
	}

	return &corev1.EventList{Items: allInstanceSetEvents}, nil
}

// mergeAndSortEvents Sort by time in descending order (latest events first)
func mergeAndSortEvents(eventLists ...*corev1.EventList) *corev1.EventList {
	var allEvents []corev1.Event
	for _, eventList := range eventLists {
		if eventList != nil {
			allEvents = append(allEvents, eventList.Items...)
		}
	}

	sort.Slice(allEvents, func(i, j int) bool {
		return allEvents[i].CreationTimestamp.After(allEvents[j].CreationTimestamp.Time)
	})

	return &corev1.EventList{Items: allEvents}
}

// validateAddonClusterVersion 检查 addonClusterVersion 是否在支持的版本列表中
func (c *ClusterProvider) validateAddonClusterVersion(
	request *coreentity.Request,
	clusterEntity *metaentity.K8sCrdClusterEntity,
) error {
	// 检查支持的版本列表是否为空
	if clusterEntity.AddonInfo.SupportedAcVersions == "" {
		slog.Error("supported ac versions is empty",
			"cluster_name", request.ClusterName,
			"addon_type", clusterEntity.AddonInfo.AddonType)
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError,
			fmt.Errorf("插件类型 %s 的 supported ac versions 配置为空", clusterEntity.AddonInfo.AddonType))
	}

	// 反序列化支持的版本列表
	var supportedAcVersions []string
	if err := json.Unmarshal([]byte(clusterEntity.AddonInfo.SupportedAcVersions), &supportedAcVersions); err != nil {
		slog.Error("failed to unmarshal supported ac versions",
			"cluster_name", request.ClusterName,
			"supported_versions", clusterEntity.AddonInfo.SupportedAcVersions,
			"error", err)
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError,
			fmt.Errorf("supported ac versions 反序列化失败: %w", err))
	}

	// 检查版本列表是否为空
	if len(supportedAcVersions) == 0 {
		slog.Error("supported ac versions list is empty",
			"cluster_name", request.ClusterName,
			"addon_type", clusterEntity.AddonInfo.AddonType)
		return dbserrors.NewK8sDbsError(dbserrors.UpdateClusterError,
			fmt.Errorf("插件类型 %s 的 supported ac versions 列表为空", clusterEntity.AddonInfo.AddonType))
	}

	// 检查请求的版本是否在支持的版本列表中
	requestedVersion := request.AddonClusterVersion
	if !lo.Contains(supportedAcVersions, requestedVersion) {
		slog.Error("addon cluster version not supported",
			"cluster_name", request.ClusterName,
			"requested_version", requestedVersion,
			"supported_versions", supportedAcVersions)
		return dbserrors.NewK8sDbsError(dbserrors.UpdateClusterError,
			fmt.Errorf("addonClusterVersion 版本 %s 不在支持的版本列表中，支持的版本: %v",
				requestedVersion, supportedAcVersions))
	}
	return nil
}
