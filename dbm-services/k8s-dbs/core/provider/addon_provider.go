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
}

// DeployAddon 安装 addon 插件
func (a *AddonProvider) DeployAddon(entity *pventity.AddonEntity) error {
	_, err := helper.CreateRequestRecord(entity, coreconst.CreateK8sNs, a.reqRecordProvider)
	if err != nil {
		return fmt.Errorf("failed to create request record for addon: %w", err)
	}
	k8sClusterConfig, err := a.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8sClusterConfig: %w", err)
	}

	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return fmt.Errorf("failed to create k8sClient: %w", err)
	}

	if err = a.installAddonHelmRelease(entity, k8sClient); err != nil {
		return fmt.Errorf("failed to install helm release: %w", err)
	}
	return nil
}

// NewAddonProvider 创建 AddonProvider 实例
func NewAddonProvider(reqRecordProvider metaprovider.ClusterRequestRecordProvider,
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
	addonHelmRepoProvider metaprovider.AddonHelmRepoProvider,
) *AddonProvider {
	return &AddonProvider{
		reqRecordProvider,
		clusterConfigProvider,
		addonHelmRepoProvider,
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
	install.Timeout = clientconst.HelmRepoDownloadTimeout
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
