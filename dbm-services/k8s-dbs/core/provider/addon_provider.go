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
	capiconst "k8s-dbs/core/api/constant"
	coreclient "k8s-dbs/core/client"
	clientconst "k8s-dbs/core/client/constants"
	coreconst "k8s-dbs/core/constant"
	"k8s-dbs/core/helper"
	corehelper "k8s-dbs/core/helper"
	pventity "k8s-dbs/core/provider/entity"
	metaprovider "k8s-dbs/metadata/provider"
	provderentity "k8s-dbs/metadata/provider/entity"
	"log/slog"

	helmcli "helm.sh/helm/v3/pkg/cli"

	"helm.sh/helm/v3/pkg/action"
	"helm.sh/helm/v3/pkg/chart/loader"
)

// AddonProvider AddonProvider 结构体
type AddonProvider struct {
	reqRecordProvider     metaprovider.ClusterRequestRecordProvider
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
	addonHelmRepoProvider metaprovider.AddonHelmRepoProvider
	clusterAddonsProvider metaprovider.K8sClusterAddonsProvider
	addonMetaProvider     metaprovider.K8sCrdStorageAddonProvider
}

// ManageAddon 管理 addon 插件
func (a *AddonProvider) ManageAddon(entity *pventity.AddonEntity, operation capiconst.AddonOperation) error {
	_, err := helper.CreateRequestRecord(entity, coreconst.CreateK8sNs, a.reqRecordProvider)
	if err != nil {
		slog.Error("Failed to create request record", "error", err)
		return fmt.Errorf("failed to create request record for addon: %w", err)
	}
	k8sClusterConfig, err := a.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		slog.Error("Failed to find k8s cluster config", "error", err)
		return fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		slog.Error("Failed to create k8s client", "error", err)
		return fmt.Errorf("failed to create k8sClient: %w", err)
	}
	switch operation {
	case capiconst.InstallAddonOP:
		if err = a.installAddonHelmRelease(entity, k8sClient); err != nil {
			slog.Error("Failed to install helm release", "error", err)
			return fmt.Errorf("failed to install helm release: %w", err)
		}
		_, err = a.createClusterAddon(entity)
		if err != nil {
			slog.Error("Failed to create cluster addon record", "error", err)
			return fmt.Errorf("failed to create cluster addon record: %w", err)
		}
	case capiconst.UninstallAddonOP:
		if err = a.UnInstallAddonHelmRelease(entity, k8sClient); err != nil {
			slog.Error("Failed to uninstall helm release", "error", err)
			return fmt.Errorf("failed to uninstall helm release: %w", err)
		}
		err = a.deleteClusterAddon(entity)
		if err != nil {
			slog.Error("Failed to delete cluster addon record", "error", err)
			return fmt.Errorf("failed to delete cluster addon record: %w", err)
		}
	case capiconst.UpgradeAddonOP:
		if err = a.UpgradeAddonHelmRelease(entity, k8sClient); err != nil {
			slog.Error("Failed to upgrade helm release", "error", err)
			return fmt.Errorf("failed to upgrade helm release: %w", err)
		}
		err = a.updateClusterAddon(entity)
		if err != nil {
			slog.Error("Failed to update cluster addon record", "error", err)
			return fmt.Errorf("failed to update cluster addon record: %w", err)
		}
	default:
		slog.Warn("Unsupported operation", "operation", operation)
		return fmt.Errorf("unsupported operation: %s", operation)
	}
	return nil
}

// NewAddonProvider 创建 AddonProvider 实例
func NewAddonProvider(
	reqRecordProvider metaprovider.ClusterRequestRecordProvider,
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
	addonHelmRepoProvider metaprovider.AddonHelmRepoProvider,
	clusterAddonsMetaProvider metaprovider.K8sClusterAddonsProvider,
	addonMetaProvider metaprovider.K8sCrdStorageAddonProvider,
) *AddonProvider {
	return &AddonProvider{
		reqRecordProvider,
		clusterConfigProvider,
		addonHelmRepoProvider,
		clusterAddonsMetaProvider,
		addonMetaProvider,
	}
}

// getAddonHelmRepository 获取 addon helm repository
func (a *AddonProvider) getAddonHelmRepository(
	entity *pventity.AddonEntity,
) (*provderentity.AddonHelmRepoEntity, error) {
	repoParams := make(map[string]interface{})
	repoParams["chart_name"] = entity.AddonType
	repoParams["chart_version"] = entity.AddonVersion

	helmRepo, err := a.addonHelmRepoProvider.FindByParams(repoParams)
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
	k8sClient *coreclient.K8sClient,
) error {
	actionConfig, err := corehelper.BuildHelmActionConfig(clientconst.AddonDefaultNamespace, k8sClient)
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
	install.ReleaseName = entity.AddonType
	install.Namespace = clientconst.AddonDefaultNamespace
	install.RepoURL = helmRepo.RepoRepository
	install.Version = entity.AddonVersion
	install.Timeout = clientconst.HelmOperationTimeout
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
			"namespace", clientconst.AddonDefaultNamespace,
			"error", err,
		)
		return fmt.Errorf("addon install failed for addonName %q in namespace %q: %w",
			entity.AddonType, clientconst.AddonDefaultNamespace, err)
	}
	return nil
}

// UnInstallAddonHelmRelease 卸载 chart release
func (a *AddonProvider) UnInstallAddonHelmRelease(
	entity *pventity.AddonEntity,
	k8sClient *coreclient.K8sClient,
) error {
	actionConfig, err := corehelper.BuildHelmActionConfig(clientconst.AddonDefaultNamespace, k8sClient)
	if err != nil {
		slog.Error("failed to build helm action config", "error", err)
		return err
	}
	unInstall := action.NewUninstall(actionConfig)
	unInstall.Timeout = clientconst.HelmOperationTimeout
	unInstall.Wait = true
	_, err = unInstall.Run(entity.AddonType)
	if err != nil {
		slog.Error("addon uninstall failed", "addonName", entity.AddonType,
			"namespace", clientconst.AddonDefaultNamespace, "error", err)
		return fmt.Errorf("addon uninstall failed for addonName %q in namespace %q: %w",
			entity.AddonType, clientconst.AddonDefaultNamespace, err)
	}
	return nil
}

// UpgradeAddonHelmRelease 更新 chart release
func (a *AddonProvider) UpgradeAddonHelmRelease(
	entity *pventity.AddonEntity,
	k8sClient *coreclient.K8sClient,
) error {
	actionConfig, err := corehelper.BuildHelmActionConfig(clientconst.AddonDefaultNamespace, k8sClient)
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
	upgrade.Namespace = clientconst.AddonDefaultNamespace
	upgrade.RepoURL = helmRepo.RepoRepository
	upgrade.Version = entity.AddonVersion
	upgrade.Timeout = clientconst.HelmOperationTimeout
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
	_, err = upgrade.Run(entity.AddonType, chart, nil)
	if err != nil {
		slog.Error("Addon upgrade failed", "addonName", entity.AddonType, "error", err)
		return fmt.Errorf("addon upgrade failed for addonName %q in namespace %q: %w",
			entity.AddonType, clientconst.AddonDefaultNamespace, err)

	}
	return nil
}

// createClusterAddon 记录 k8s 集群 addon 的安装信息
func (a *AddonProvider) createClusterAddon(entity *pventity.AddonEntity) (
	*provderentity.K8sClusterAddonsEntity,
	error,
) {
	storageAddon, err := a.getStorageAddon(entity)
	if err != nil {
		slog.Error("failed to get storage addon", "error", err)
		return nil, err
	}

	clusterAddon := provderentity.K8sClusterAddonsEntity{
		K8sClusterName: entity.K8sClusterName,
		AddonID:        storageAddon.ID,
	}

	addedClusterAddon, err := a.clusterAddonsProvider.CreateClusterAddon(&clusterAddon)
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
func (a *AddonProvider) deleteClusterAddon(entity *pventity.AddonEntity) error {
	storageAddon, err := a.getStorageAddon(entity)
	if err != nil {
		slog.Error("failed to get storage addon", "error", err)
		return err
	}
	caParams := map[string]interface{}{
		"addon_id":         storageAddon.ID,
		"k8s_cluster_name": entity.K8sClusterName,
	}
	clusterAddons, err := a.clusterAddonsProvider.FindClusterAddonByParams(caParams)
	if err != nil {
		slog.Error("failed to find cluster addon record", "caParams", caParams, "error", err)
	}
	if len(clusterAddons) == 1 {
		_, err := a.clusterAddonsProvider.DeleteClusterAddon(clusterAddons[0].ID)
		if err != nil {
			slog.Error("failed to delete cluster addon record", "error", err, "addon_id", clusterAddons[0].ID)
			return err
		}
	}
	return nil
}

// updateClusterAddon 更新 k8s 集群 addon 的安装信息
func (a *AddonProvider) updateClusterAddon(entity *pventity.AddonEntity) error {
	storageAddon, err := a.getStorageAddon(entity)
	if err != nil {
		slog.Error("failed to get storage addon", "error", err)
		return err
	}
	caParams := map[string]interface{}{
		"addon_id":         storageAddon.ID,
		"k8s_cluster_name": entity.K8sClusterName,
	}
	clusterAddons, err := a.clusterAddonsProvider.FindClusterAddonByParams(caParams)
	if err != nil {
		slog.Error("failed to find cluster addon record", "caParams", caParams, "error", err)
		return err
	}
	if len(clusterAddons) == 1 {
		_, err := a.clusterAddonsProvider.UpdateClusterAddon(&clusterAddons[0])
		if err != nil {
			slog.Error("failed to update cluster addon record", "error", err, "addon_id", clusterAddons[0].ID)
			return err
		}
	}
	return nil
}

// getStorageAddon 获取 storage addons
func (a *AddonProvider) getStorageAddon(entity *pventity.AddonEntity) (*provderentity.K8sCrdStorageAddonEntity, error) {
	saParams := map[string]interface{}{
		"addon_type":    entity.AddonType,
		"addon_version": entity.AddonVersion,
	}
	saEntities, err := a.addonMetaProvider.FindStorageAddonByParams(saParams)
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
