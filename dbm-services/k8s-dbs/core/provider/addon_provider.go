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
	pventity "k8s-dbs/core/provider/entity"
	metaprovider "k8s-dbs/metadata/provider"
	"log/slog"

	helmcli "helm.sh/helm/v3/pkg/cli"

	"helm.sh/helm/v3/pkg/action"
	"helm.sh/helm/v3/pkg/chart/loader"
)

// AddonProvider AddonProvider 结构体
type AddonProvider struct {
	reqRecordProvider     metaprovider.ClusterRequestRecordProvider
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
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

	actionConfig, err := k8sClient.BuildHelmConfig(clientconst.AddonDefaultNamespace)
	if err != nil {
		slog.Error("failed to build Helm configuration",
			"namespace", clientconst.AddonDefaultNamespace,
			"error", err,
		)
		return fmt.Errorf("failed to build Helm configuration for namespace %q: %w", clientconst.AddonDefaultNamespace, err)
	}

	install := action.NewInstall(actionConfig)
	install.ReleaseName = entity.AddonType
	install.Namespace = clientconst.AddonDefaultNamespace
	install.RepoURL = entity.AddonRepoURL
	install.Version = entity.AddonVersion
	install.Timeout = clientconst.HelmRepoDownloadTimeout
	install.CreateNamespace = true
	install.Wait = true
	install.Username = entity.AddonRepoUserName
	install.Password = entity.AddonRepoPassword

	chartRequested, err := install.ChartPathOptions.LocateChart(install.ReleaseName, helmcli.New())
	if err != nil {
		return fmt.Errorf("下载失败\n%s", err)
	}

	chart, err := loader.Load(chartRequested)
	if err != nil {
		return fmt.Errorf("加载失败\n%s", err)
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

// NewAddonProvider 创建 AddonProvider 实例
func NewAddonProvider(reqRecordProvider metaprovider.ClusterRequestRecordProvider,
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
) *AddonProvider {
	return &AddonProvider{
		reqRecordProvider,
		clusterConfigProvider,
	}
}
