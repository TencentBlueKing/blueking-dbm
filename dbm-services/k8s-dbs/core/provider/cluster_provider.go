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
	coreclient "k8s-dbs/core/client"
	clientconst "k8s-dbs/core/client/constants"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	corehelper "k8s-dbs/core/helper"
	metaprovider "k8s-dbs/metadata/provider"
	provderentity "k8s-dbs/metadata/provider/entity"
	"log/slog"
	"sort"

	kbworkloadv1 "github.com/apecloud/kubeblocks/apis/workloads/v1alpha1"
	"helm.sh/helm/v3/pkg/action"
	"helm.sh/helm/v3/pkg/chart/loader"
	helmcli "helm.sh/helm/v3/pkg/cli"
	"k8s.io/apimachinery/pkg/runtime/schema"

	kbtypes "github.com/apecloud/kbcli/pkg/types"
	kbappv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	"github.com/pkg/errors"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
)

// ClusterProvider 集群管理核心服务
type ClusterProvider struct {
	addonMetaProvider       metaprovider.K8sCrdStorageAddonProvider
	clusterMetaProvider     metaprovider.K8sCrdClusterProvider
	componentMetaProvider   metaprovider.K8sCrdComponentProvider
	cdMetaProvider          metaprovider.K8sCrdClusterDefinitionProvider
	cmpdMetaProvider        metaprovider.K8sCrdCmpdProvider
	cmpvMetaProvider        metaprovider.K8sCrdCmpvProvider
	clusterConfigProvider   metaprovider.K8sClusterConfigProvider
	reqRecordProvider       metaprovider.ClusterRequestRecordProvider
	releaseMetaProvider     metaprovider.AddonClusterReleaseProvider
	clusterHelmRepoProvider metaprovider.AddonClusterHelmRepoProvider
}

// ClusterProviderBuilder ClusterProvider builder
type ClusterProviderBuilder struct {
	addonMetaProvider       metaprovider.K8sCrdStorageAddonProvider
	clusterMetaProvider     metaprovider.K8sCrdClusterProvider
	componentMetaProvider   metaprovider.K8sCrdComponentProvider
	cdMetaProvider          metaprovider.K8sCrdClusterDefinitionProvider
	cmpdMetaProvider        metaprovider.K8sCrdCmpdProvider
	cmpvMetaProvider        metaprovider.K8sCrdCmpvProvider
	clusterConfigProvider   metaprovider.K8sClusterConfigProvider
	reqRecordProvider       metaprovider.ClusterRequestRecordProvider
	releaseMetaProvider     metaprovider.AddonClusterReleaseProvider
	clusterHelmRepoProvider metaprovider.AddonClusterHelmRepoProvider
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

// WithClusterHelmRepoProvider 设置 ClusterProviderBuilder
func (c *ClusterProviderBuilder) WithClusterHelmRepoProvider(
	p metaprovider.AddonClusterHelmRepoProvider,
) *ClusterProviderBuilder {
	c.clusterHelmRepoProvider = p
	return c
}

// WithAddonMetaProvider 设置 AddonMetaProvider
func (c *ClusterProviderBuilder) WithAddonMetaProvider(
	p metaprovider.K8sCrdStorageAddonProvider,
) *ClusterProviderBuilder {
	c.addonMetaProvider = p
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
	if c.clusterHelmRepoProvider == nil {
		return nil, errors.New("clusterHelmRepoProvider is required")
	}
	if c.addonMetaProvider == nil {
		return nil, errors.New("addonMetaProvider is required")
	}
	return &ClusterProvider{
		clusterMetaProvider:     c.clusterMetaProvider,
		componentMetaProvider:   c.componentMetaProvider,
		cdMetaProvider:          c.cdMetaProvider,
		cmpdMetaProvider:        c.cmpdMetaProvider,
		cmpvMetaProvider:        c.cmpvMetaProvider,
		clusterConfigProvider:   c.clusterConfigProvider,
		reqRecordProvider:       c.reqRecordProvider,
		releaseMetaProvider:     c.releaseMetaProvider,
		clusterHelmRepoProvider: c.clusterHelmRepoProvider,
		addonMetaProvider:       c.addonMetaProvider,
	}, nil
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
func (c *ClusterProvider) CreateCluster(request *coreentity.Request) error {
	// 记录 request record
	addedRequestEntity, err := corehelper.SaveAuditLog(c.reqRecordProvider, request, coreconst.CreateCluster)
	if err != nil {
		return fmt.Errorf("failed to create request entity: %w", err)
	}

	// 获取 k8s 集群配置
	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		return fmt.Errorf("failed to get k8s cluster config for name %q: %w", request.K8sClusterName, err)
	}

	// 获取 K8sClient
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		return fmt.Errorf("failed to create k8s client for cluster %q: %w", request.K8sClusterName, err)
	}

	if err = c.saveClusterMetaData(request, addedRequestEntity.RequestID, k8sClusterConfig.ID); err != nil {
		slog.Error("failed to save cluster meta data", "err", err)
		return err
	}

	// 安装 cluster
	values, err := c.installHelmRelease(request, k8sClient)
	if err != nil {
		slog.Error("failed to install helm release", "error", err)
		return err
	}

	// 保存 addon cluster release
	clusterRelease, err := buildClusterReleaseEntity(
		k8sClusterConfig.ID,
		request,
		coreconst.DefaultUserName,
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

// saveClusterMetaData 记录集群元数据
func (c *ClusterProvider) saveClusterMetaData(
	request *coreentity.Request,
	requestID string,
	k8sClusterConfigID uint64,
) error {
	// 记录 cluster 元数据
	addedClusterEntity, err := c.createClusterEntity(request, requestID, k8sClusterConfigID)
	if err != nil {
		return err
	}

	clusterID := addedClusterEntity.ID
	// 记录 component 元数据
	_, err = c.createComponentEntity(request, clusterID)
	if err != nil {
		return err
	}
	return nil
}

// UpdateCluster 更新集群
func (c *ClusterProvider) UpdateCluster(request *coreentity.Request) error {
	_, err := corehelper.SaveAuditLog(c.reqRecordProvider, request, coreconst.PartialUpdateCluster)
	if err != nil {
		slog.Error("failed to create request record", "error", err)
		return err
	}

	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		slog.Error("failed to find k8s cluster config", "error", err)
		return err
	}

	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		slog.Error("failed to create k8s client", "error", err)
		return err
	}

	values, err := c.updateClusterRelease(request, k8sClient)
	if err != nil {
		slog.Error("failed to update helm release", "error", err)
		return err
	}

	jsonData, err := json.Marshal(values)
	if err != nil {
		slog.Error("failed to marshal release values",
			"release_name", request.ClusterName,
			"error", err,
		)
		return err
	}

	paramsRelease := map[string]interface{}{
		"k8s_cluster_config_id": k8sClusterConfig.ID,
		"release_name":          request.ClusterName,
		"namespace":             request.Namespace,
	}
	releaseEntity, err := c.releaseMetaProvider.FindByParams(paramsRelease)
	if err != nil {
		return err
	}
	releaseEntity.ChartValues = string(jsonData)
	_, err = c.releaseMetaProvider.UpdateClusterRelease(releaseEntity)
	if err != nil {
		slog.Error("failed to update cluster release",
			"release_name", request.ClusterName,
			"namespace", request.Namespace,
			"error", err,
		)
		return err
	}
	return nil
}

// PartialUpdateCluster 局部更新集群
func (c *ClusterProvider) PartialUpdateCluster(request *coreentity.Request) error {
	_, err := corehelper.SaveAuditLog(c.reqRecordProvider, request, coreconst.PartialUpdateCluster)
	if err != nil {
		slog.Error("failed to create request record", "error", err)
		return err
	}

	k8sClusterConfig, err := c.clusterConfigProvider.FindConfigByName(request.K8sClusterName)
	if err != nil {
		slog.Error("failed to find k8s cluster config", "error", err)
		return err
	}

	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
	if err != nil {
		slog.Error("failed to create k8s client", "error", err)
		return err
	}

	values, err := c.partialUpdateClusterRelease(request, k8sClient)
	if err != nil {
		slog.Error("failed to update helm release", "error", err)
		return err
	}

	jsonData, err := json.Marshal(values)
	if err != nil {
		slog.Error("failed to marshal release values",
			"release_name", request.ClusterName,
			"error", err,
		)
		return err
	}

	paramsRelease := map[string]interface{}{
		"k8s_cluster_config_id": k8sClusterConfig.ID,
		"release_name":          request.ClusterName,
		"namespace":             request.Namespace,
	}
	releaseEntity, err := c.releaseMetaProvider.FindByParams(paramsRelease)
	if err != nil {
		return err
	}
	releaseEntity.ChartValues = string(jsonData)
	_, err = c.releaseMetaProvider.UpdateClusterRelease(releaseEntity)
	if err != nil {
		slog.Error("failed to partial update cluster release",
			"release_name", request.ClusterName,
			"namespace", request.Namespace,
			"error", err,
		)
		return err
	}
	return nil
}

// DeleteCluster 删除集群
func (c *ClusterProvider) DeleteCluster(request *coreentity.Request) error {
	_, err := corehelper.SaveAuditLog(c.reqRecordProvider, request, coreconst.DeleteCluster)
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

	clusterEntity, err := c.clusterMetaProvider.FindByParams(
		map[string]interface{}{
			"k8s_cluster_config_id": k8sClusterConfig.ID,
			"cluster_name":          request.ClusterName,
			"namespace":             request.Namespace,
		})
	if err != nil {
		return err
	}
	_, err = c.clusterMetaProvider.DeleteClusterByID(clusterEntity.ID)
	if err != nil {
		return err
	}

	releaseEntity, err := c.releaseMetaProvider.FindByParams(
		map[string]interface{}{
			"k8s_cluster_config_id": k8sClusterConfig.ID,
			"release_name":          request.ClusterName,
			"namespace":             request.Namespace,
		})
	if err != nil {
		return err
	}
	_, err = c.releaseMetaProvider.DeleteClusterReleaseByID(releaseEntity.ID)
	if err != nil {
		return err
	}

	if err = coreclient.DeleteStorageAddonCluster(k8sClient, request.ClusterName, request.Namespace); err != nil {
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

// createClusterEntity Save and return the cluster instance
func (c *ClusterProvider) createClusterEntity(
	request *coreentity.Request,
	requestID string,
	k8sClusterConfigID uint64,
) (*provderentity.K8sCrdClusterEntity, error) {
	addonParams := map[string]interface{}{
		"addon_type":    request.StorageAddonType,
		"addon_version": request.StorageAddonVersion,
	}
	storageAddon, err := c.addonMetaProvider.FindStorageAddonByParams(addonParams)
	if err != nil {
		slog.Error("failed to get storage addon", "error", err)
		return nil, err
	}
	if len(storageAddon) != 1 {
		errMsg := fmt.Sprintf("expected 1 storage addon, found %d", len(storageAddon))
		slog.Error("failed to get storage addon", "error", errMsg)
		return nil, err
	}

	clusterEntity := &provderentity.K8sCrdClusterEntity{
		AddonID:             storageAddon[0].ID,
		AddonClusterVersion: request.AddonClusterVersion,
		ClusterName:         request.ClusterName,
		ClusterAlias:        request.ClusterAlias,
		Namespace:           request.Namespace,
		RequestID:           requestID,
		K8sClusterConfigID:  k8sClusterConfigID,
		BkBizID:             request.BkBizID,
		BkBizName:           request.BkBizName,
		BkAppAbbr:           request.BkAppAbbr,
		BkAppCode:           request.BKAuth.BkAppCode,
		CreatedBy:           request.BKAuth.BkUserName,
	}
	addedClusterEntity, err := c.clusterMetaProvider.CreateCluster(clusterEntity)
	if err != nil {
		slog.Error("failed to create cluster entity", "error", err)
		return nil, err
	}
	return addedClusterEntity, nil
}

// createComponentEntity Save and return an array of component instances
func (c *ClusterProvider) createComponentEntity(
	request *coreentity.Request,
	crdClusterID uint64,
) ([]*provderentity.K8sCrdComponentEntity, error) {
	var compEntityList []*provderentity.K8sCrdComponentEntity
	for _, comp := range request.ComponentList {
		compName := request.Metadata.ClusterName + "-" + comp.ComponentName
		componentEntity := &provderentity.K8sCrdComponentEntity{
			ComponentName: compName,
			CrdClusterID:  crdClusterID,
			CreatedBy:     request.BKAuth.BkUserName,
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
) (*provderentity.AddonClusterReleaseEntity, error) {
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

	return &provderentity.AddonClusterReleaseEntity{
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

// installHelmRelease 安装 chart
func (c *ClusterProvider) installHelmRelease(
	request *coreentity.Request,
	k8sClient *coreclient.K8sClient,
) (map[string]interface{}, error) {
	actionConfig, err := corehelper.BuildHelmActionConfig(request.Namespace, k8sClient)
	if err != nil {
		slog.Error("failed to build helm action config", "error", err)
		return nil, err
	}
	helmRepo, err := c.getClusterHelmRepository(request)
	if err != nil {
		slog.Error("failed to get helm repo", "error", err)
		return nil, err
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
	install.Timeout = clientconst.HelmOperationTimeout
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
	err = coreclient.MergeValues(values, request)
	if err != nil {
		slog.Error("failed to merge dynamic values", "error", err)
		return nil, fmt.Errorf("failed to merge dynamic values  %w", err)
	}
	_, err = install.Run(chart, values)
	if err != nil {
		slog.Error("cluster install failed", "clusterName", request.ClusterName, "error", err)
		return nil, fmt.Errorf("failed to install cluster %s: %w", request.ClusterName, err)
	}
	return values, nil
}

// updateClusterRelease 更新 release
func (c *ClusterProvider) updateClusterRelease(
	request *coreentity.Request,
	k8sClient *coreclient.K8sClient,
) (map[string]interface{}, error) {
	actionConfig, err := corehelper.BuildHelmActionConfig(request.Namespace, k8sClient)
	if err != nil {
		slog.Error("failed to build helm action config", "error", err)
		return nil, err
	}
	values, err := c.doUpdateClusterRelease(request, actionConfig, false)
	if err != nil {
		slog.Error("cluster update failed", "clusterName", request.ClusterName, "error", err)
		return nil, err
	}
	return values, nil
}

// partialUpdateClusterRelease 局部更新 release
func (c *ClusterProvider) partialUpdateClusterRelease(
	request *coreentity.Request,
	k8sClient *coreclient.K8sClient,
) (map[string]interface{}, error) {
	actionConfig, err := corehelper.BuildHelmActionConfig(request.Namespace, k8sClient)
	if err != nil {
		slog.Error("failed to build helm action config", "error", err)
		return nil, err
	}

	values, err := c.doUpdateClusterRelease(request, actionConfig, true)
	if err != nil {
		slog.Error("cluster partial update failed", "clusterName", request.ClusterName, "error", err)
		return nil, err
	}
	return values, nil
}

// doUpdateClusterRelease 执行更新 release
func (c *ClusterProvider) doUpdateClusterRelease(
	request *coreentity.Request,
	actionConfig *action.Configuration,
	isPartial bool,
) (map[string]interface{}, error) {
	helmRepo, err := c.getClusterHelmRepository(request)
	if err != nil {
		slog.Error("failed to get helm repo", "error", err)
		return nil, err
	}
	upgrade := action.NewUpgrade(actionConfig)
	upgrade.Namespace = request.Namespace
	upgrade.RepoURL = helmRepo.RepoRepository
	upgrade.Version = request.AddonClusterVersion
	upgrade.Timeout = clientconst.HelmOperationTimeout
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
		getValuesAction := action.NewGetValues(actionConfig)
		releaseValues, err := getValuesAction.Run(request.ClusterName)
		if err != nil {
			return nil, err
		}

		if err = coreclient.MergeValues(releaseValues, request); err != nil {
			return nil, err
		}
		values = releaseValues
	} else {
		chartValues := chart.Values
		err = coreclient.MergeValues(chartValues, request)
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
) (*provderentity.AddonClusterHelmRepoEntity, error) {
	repoParams := make(map[string]interface{})
	repoParams["chart_name"] = request.StorageAddonType + "-cluster"
	repoParams["chart_version"] = request.StorageAddonVersion

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
	k8sClient, err := coreclient.NewK8sClient(k8sClusterConfig)
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
func (c *ClusterProvider) getInstanceSetEvents(k8sClient *coreclient.K8sClient, namespace, clusterName string) (
	*corev1.EventList, error) {
	crd := &coreentity.CustomResourceDefinition{
		GroupVersionResource: InstanceSetGVR(),
		Namespace:            namespace,
		Labels: map[string]string{
			coreconst.InstanceName: clusterName,
		},
	}

	instanceSetList, err := coreclient.ListCRD(k8sClient, crd)
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
