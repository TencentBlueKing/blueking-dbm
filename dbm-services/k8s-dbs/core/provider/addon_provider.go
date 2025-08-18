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
	"errors"
	"fmt"
	commentity "k8s-dbs/common/entity"
	commutil "k8s-dbs/common/util"
	coreconst "k8s-dbs/core/constant"
	pventity "k8s-dbs/core/entity"
	coreutil "k8s-dbs/core/util"
	dbserrors "k8s-dbs/errors"
	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
	metautil "k8s-dbs/metadata/util"
	"log/slog"

	helmcli "helm.sh/helm/v3/pkg/cli"

	"helm.sh/helm/v3/pkg/action"
	"helm.sh/helm/v3/pkg/chart/loader"
)

// AddonProvider AddonProvider 结构体
type AddonProvider struct {
	reqRecordMeta     metaprovider.ClusterRequestRecordProvider
	clusterConfigMeta metaprovider.K8sClusterConfigProvider
	addonHelmRepoMeta metaprovider.AddonHelmRepoProvider
	clusterAddonsMeta metaprovider.K8sClusterAddonsProvider
	addonMeta         metaprovider.K8sCrdStorageAddonProvider
}

// AddonProviderOption AddonProvider 的函数选项
type AddonProviderOption func(*AddonProvider)

// AddonProviderBuilder 辅助构建 AddonProvider
type AddonProviderBuilder struct{}

// WithReqRecordMeta 设置 ClusterRequestRecordProvider
func (a *AddonProviderBuilder) WithReqRecordMeta(
	provider metaprovider.ClusterRequestRecordProvider,
) AddonProviderOption {
	return func(a *AddonProvider) {
		a.reqRecordMeta = provider
	}
}

// WithClusterConfigMeta 设置 K8sClusterConfigMeta
func (a *AddonProviderBuilder) WithClusterConfigMeta(
	provider metaprovider.K8sClusterConfigProvider,
) AddonProviderOption {
	return func(a *AddonProvider) {
		a.clusterConfigMeta = provider
	}
}

// WithAddonHelmRepoMeta 设置 addonHelmRepoMeta
func (a *AddonProviderBuilder) WithAddonHelmRepoMeta(
	provider metaprovider.AddonHelmRepoProvider,
) AddonProviderOption {
	return func(a *AddonProvider) {
		a.addonHelmRepoMeta = provider
	}
}

// WithClusterAddonMeta 设置 K8sClusterAddonsProvider
func (a *AddonProviderBuilder) WithClusterAddonMeta(
	provider metaprovider.K8sClusterAddonsProvider,
) AddonProviderOption {
	return func(a *AddonProvider) {
		a.clusterAddonsMeta = provider
	}
}

// WithAddonMeta 配置 K8sCrdStorageAddonProvider
func (a *AddonProviderBuilder) WithAddonMeta(
	provider metaprovider.K8sCrdStorageAddonProvider,
) AddonProviderOption {
	return func(a *AddonProvider) {
		a.addonMeta = provider
	}
}

// NewAddonProvider 创建 AddonProvider 实例
func NewAddonProvider(opts ...AddonProviderOption) (*AddonProvider, error) {
	provider := &AddonProvider{}
	for _, opt := range opts {
		opt(provider)
	}
	if err := provider.validateProvider(); err != nil {
		slog.Error("failed to validate addon provider", "error", err)
		return nil, err
	}
	return provider, nil
}

// validateProvider 验证 AddonProvider 必要字段
func (a *AddonProvider) validateProvider() error {
	if a.reqRecordMeta == nil {
		slog.Error("reqRecordProvider is nil")
		return errors.New("reqRecordProvider is nil")
	}
	if a.clusterConfigMeta == nil {
		slog.Error("clusterConfigProvider is nil")
		return errors.New("clusterConfigProvider is nil")
	}
	if a.addonMeta == nil {
		slog.Error("addonMetaProvider is nil")
		return errors.New("addonMetaProvider is nil")
	}
	if a.addonHelmRepoMeta == nil {
		slog.Error("addonHelmRepoMeta is nil")
		return errors.New("addonHelmRepoMeta is nil")
	}
	if a.clusterAddonsMeta == nil {
		slog.Error("clusterAddonsMeta is nil")
		return errors.New("clusterAddonsMeta is nil")
	}
	return nil
}

// ManageAddon 管理 addon 插件
func (a *AddonProvider) ManageAddon(
	dbsCtx *commentity.DbsContext,
	entity *pventity.AddonEntity,
	operation coreconst.AddonOperation,
) error {
	_, err := metautil.SaveCommonAuditV2(a.reqRecordMeta, dbsCtx)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateMetaDataError, err)
	}
	k8sClusterConfig, err := a.clusterConfigMeta.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return dbserrors.NewK8sDbsError(dbserrors.CreateK8sClientError, err)
	}
	switch operation {
	case coreconst.InstallAddonOP:
		if err = a.installAddonHelmRelease(entity, k8sClient); err != nil {
			return fmt.Errorf("failed to install helm release: %w", err)
		}
		_, err = a.createClusterAddon(dbsCtx, entity)
		if err != nil {
			return fmt.Errorf("failed to create cluster addon record: %w", err)
		}
	case coreconst.UninstallAddonOP:
		if err = a.UnInstallAddonHelmRelease(entity, k8sClient); err != nil {
			return fmt.Errorf("failed to uninstall helm release: %w", err)
		}
		if err = a.deleteClusterAddon(dbsCtx, entity); err != nil {
			return fmt.Errorf("failed to delete cluster addon record: %w", err)
		}
	case coreconst.UpgradeAddonOP:
		if err = a.UpgradeAddonHelmRelease(entity, k8sClient); err != nil {
			return fmt.Errorf("failed to upgrade helm release: %w", err)
		}
		if err = a.updateClusterAddon(dbsCtx, entity); err != nil {
			return fmt.Errorf("failed to update cluster addon record: %w", err)
		}
	default:
		return fmt.Errorf("unsupported operation: %s", operation)
	}
	return nil
}

// getAddonHelmRepository 获取 addon helm repository
func (a *AddonProvider) getAddonHelmRepository(
	entity *pventity.AddonEntity,
) (*metaentity.AddonHelmRepoEntity, error) {
	repoParams := &metaentity.HelmRepoQueryParams{
		ChartName:    entity.AddonType,
		ChartVersion: entity.AddonVersion,
	}
	helmRepo, err := a.addonHelmRepoMeta.FindByParams(repoParams)
	if err != nil {
		slog.Error("failed to find helm repo for addon", "addon_type",
			entity.AddonType, "addon_version", entity.AddonVersion, "error", err)
		return nil, err
	}
	return helmRepo, nil
}

// installAddonHelmRelease 安装 chart
func (a *AddonProvider) installAddonHelmRelease(
	entity *pventity.AddonEntity,
	k8sClient *commutil.K8sClient,
) error {
	actionConfig, err := coreutil.BuildHelmActionConfig(coreconst.AddonDefaultNamespace, k8sClient)
	if err != nil {
		slog.Error("failed to build helm action config", "error", err)
		return err
	}
	helmRepo, err := a.getAddonHelmRepository(entity)
	if err != nil {
		slog.Error("failed to get helm repo", "error", err)
		return err
	}
	install := action.NewInstall(actionConfig)
	install.ReleaseName = getAddonReleaseName(entity)
	install.Namespace = coreconst.AddonDefaultNamespace
	install.RepoURL = helmRepo.RepoRepository
	install.Version = entity.AddonVersion
	install.Timeout = coreconst.HelmOperationTimeout
	install.CreateNamespace = true
	install.Wait = true
	install.Username = helmRepo.RepoUsername
	install.Password = helmRepo.RepoPassword
	chartRequested, err := install.ChartPathOptions.LocateChart(install.ReleaseName, helmcli.New())
	if err != nil {
		slog.Error("failed to locate helm chart requested", "error", err)
		return fmt.Errorf("failed to locate helm chart requested\n%s", err)
	}
	chart, err := loader.Load(chartRequested)
	if err != nil {
		slog.Error("failed to load helm chart requested", "error", err)
		return fmt.Errorf("failed to load helm chart requested\n%s", err)
	}

	_, err = install.Run(chart, nil)
	if err != nil {
		slog.Error("Addon install failed",
			"addonName", entity.AddonType,
			"namespace", coreconst.AddonDefaultNamespace,
			"error", err,
		)
		return fmt.Errorf("addon install failed for addonName %q in namespace %q: %w",
			entity.AddonType, coreconst.AddonDefaultNamespace, err)
	}
	return nil
}

// UnInstallAddonHelmRelease 卸载 chart release
func (a *AddonProvider) UnInstallAddonHelmRelease(
	entity *pventity.AddonEntity,
	k8sClient *commutil.K8sClient,
) error {
	actionConfig, err := coreutil.BuildHelmActionConfig(coreconst.AddonDefaultNamespace, k8sClient)
	if err != nil {
		slog.Error("failed to build helm action config", "error", err)
		return err
	}
	unInstall := action.NewUninstall(actionConfig)
	unInstall.Timeout = coreconst.HelmOperationTimeout
	unInstall.Wait = true
	releaseName := getAddonReleaseName(entity)
	if entity.IsHistory {
		releaseName = entity.AddonType
	}
	_, err = unInstall.Run(releaseName)
	if err != nil {
		slog.Error("addon uninstall failed", "addonName", entity.AddonType,
			"namespace", coreconst.AddonDefaultNamespace, "error", err)
		return fmt.Errorf("addon uninstall failed for addonName %q in namespace %q: %w",
			entity.AddonType, coreconst.AddonDefaultNamespace, err)
	}
	return nil
}

// getAddonReleaseName 获取 addon release 名称
func getAddonReleaseName(entity *pventity.AddonEntity) string {
	return fmt.Sprintf("%s-%s", entity.AddonType, entity.AddonVersion)
}

// UpgradeAddonHelmRelease 更新 chart release
func (a *AddonProvider) UpgradeAddonHelmRelease(
	entity *pventity.AddonEntity,
	k8sClient *commutil.K8sClient,
) error {
	actionConfig, err := coreutil.BuildHelmActionConfig(coreconst.AddonDefaultNamespace, k8sClient)
	if err != nil {
		slog.Error("failed to build helm action config", "error", err)
		return err
	}
	helmRepo, err := a.getAddonHelmRepository(entity)
	if err != nil {
		slog.Error("failed to get helm repo", "error", err)
		return err
	}
	upgrade := action.NewUpgrade(actionConfig)
	upgrade.Namespace = coreconst.AddonDefaultNamespace
	upgrade.RepoURL = helmRepo.RepoRepository
	upgrade.Version = entity.AddonVersion
	upgrade.Timeout = coreconst.HelmOperationTimeout
	upgrade.Wait = true
	upgrade.Username = helmRepo.RepoUsername
	upgrade.Password = helmRepo.RepoPassword
	chartRequested, err := upgrade.ChartPathOptions.LocateChart(entity.AddonType, helmcli.New())
	if err != nil {
		slog.Error("failed to locate helm chart requested", "error", err)
		return fmt.Errorf("failed to locate helm chart requested\n%s", err)
	}
	chart, err := loader.Load(chartRequested)
	if err != nil {
		slog.Error("failed to load helm chart requested", "error", err)
		return fmt.Errorf("failed to load helm chart requested\n%s", err)
	}
	releaseName := getAddonReleaseName(entity)
	if entity.IsHistory {
		releaseName = entity.AddonType
	}
	_, err = upgrade.Run(releaseName, chart, nil)
	if err != nil {
		slog.Error("Addon upgrade failed", "addonName", entity.AddonType, "error", err)
		return fmt.Errorf("addon upgrade failed for addonName %q in namespace %q: %w",
			entity.AddonType, coreconst.AddonDefaultNamespace, err)

	}
	return nil
}

// createClusterAddon 记录 k8s 集群 addon 的安装信息
func (a *AddonProvider) createClusterAddon(
	dbsCtx *commentity.DbsContext,
	entity *pventity.AddonEntity,
) (
	*metaentity.K8sClusterAddonsEntity,
	error,
) {
	storageAddon, err := a.getStorageAddon(entity)
	if err != nil {
		slog.Error("failed to get storage addon", "error", err)
		return nil, err
	}

	clusterAddon := metaentity.K8sClusterAddonsEntity{
		K8sClusterName: entity.K8sClusterName,
		AddonID:        storageAddon.ID,
		CreatedBy:      dbsCtx.BkAuth.BkUserName,
		UpdatedBy:      dbsCtx.BkAuth.BkUserName,
	}

	addedClusterAddon, err := a.clusterAddonsMeta.CreateClusterAddon(&clusterAddon)
	if err != nil {
		slog.Error("failed to save cluster addon record",
			"error", err,
			"cluster_name", entity.K8sClusterName,
			"addon_id", storageAddon.ID)
		return nil, err
	}
	return addedClusterAddon, nil
}

// deleteClusterAddon 删除 k8s 集群 addon 的安装信息
func (a *AddonProvider) deleteClusterAddon(_ *commentity.DbsContext, entity *pventity.AddonEntity) error {
	storageAddon, err := a.getStorageAddon(entity)
	if err != nil {
		slog.Error("failed to get storage addon", "error", err)
		return err
	}

	clusterAddonParams := &metaentity.K8sClusterAddonQueryParams{
		K8sClusterName: entity.K8sClusterName,
		AddonID:        storageAddon.ID,
	}
	clusterAddons, err := a.clusterAddonsMeta.FindClusterAddonByParams(clusterAddonParams)
	if err != nil {
		slog.Error("failed to find cluster addon record", "caParams", clusterAddonParams, "error", err)
	}
	if len(clusterAddons) == 1 {
		_, err := a.clusterAddonsMeta.DeleteClusterAddon(clusterAddons[0].ID)
		if err != nil {
			slog.Error("failed to delete cluster addon record", "error", err, "addon_id", clusterAddons[0].ID)
			return err
		}
	}
	return nil
}

// updateClusterAddon 更新 k8s 集群 addon 的安装信息
func (a *AddonProvider) updateClusterAddon(dbsCtx *commentity.DbsContext, entity *pventity.AddonEntity) error {
	storageAddon, err := a.getStorageAddon(entity)
	if err != nil {
		slog.Error("failed to get storage addon", "error", err)
		return err
	}
	clusterAddonParams := &metaentity.K8sClusterAddonQueryParams{
		K8sClusterName: entity.K8sClusterName,
		AddonID:        storageAddon.ID,
	}
	clusterAddons, err := a.clusterAddonsMeta.FindClusterAddonByParams(clusterAddonParams)
	if err != nil {
		slog.Error("failed to find cluster addon record", "caParams", clusterAddonParams, "error", err)
		return err
	}
	if len(clusterAddons) == 1 {
		clusterAddon := &clusterAddons[0]
		clusterAddon.UpdatedBy = dbsCtx.BkAuth.BkUserName
		_, err := a.clusterAddonsMeta.UpdateClusterAddon(clusterAddon)
		if err != nil {
			slog.Error("failed to update cluster addon record", "error", err, "addon_id", clusterAddons[0].ID)
			return err
		}
	}
	return nil
}

// getStorageAddon 获取 storage addons
func (a *AddonProvider) getStorageAddon(entity *pventity.AddonEntity) (*metaentity.K8sCrdStorageAddonEntity, error) {
	addonQueryParams := &metaentity.AddonQueryParams{
		AddonType:    entity.AddonType,
		AddonVersion: entity.AddonVersion,
	}
	saEntities, err := a.addonMeta.FindStorageAddonByParams(addonQueryParams)
	if err != nil {
		slog.Error("failed to find addon meta data", "error", err,
			"addon_type", entity.AddonType, "addon_version", entity.AddonVersion)
		return nil, err
	}
	if len(saEntities) == 0 {
		slog.Error("no matching addon meta data found",
			"addon_type", entity.AddonType, "addon_version", entity.AddonVersion)
		return nil, err
	}
	return saEntities[0], nil
}
