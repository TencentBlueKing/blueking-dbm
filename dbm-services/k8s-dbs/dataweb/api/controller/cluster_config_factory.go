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

package controller

import (
	"fmt"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	webreq "k8s-dbs/dataweb/vo/request"
	"k8s-dbs/errors"
	"log/slog"
	"regexp"
	"strconv"
)

// validateClusterName 检查 clusterName 是否合法
func validateClusterName(clusterName string) error {
	var clusterNameRegex = regexp.MustCompile(`^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$`)
	if !clusterNameRegex.MatchString(clusterName) {
		return fmt.Errorf("%v 集群名称格式不合法，只能包含小写字母、数字和连字符(-)，并且可以用点(.)分隔", clusterName)
	}

	if len(clusterName) > 53 {
		return fmt.Errorf("集群名称长度不合法，当前长度 %d 超过最大长度 53", len(clusterName))
	}
	return nil
}

// ClusterConfigBuilder 构建集群部署配置结构体
type ClusterConfigBuilder interface {
	BuildConfig(*webreq.ClusterInstallRequest) (*coreentity.Request, error)
	BuildBasicConfig(*webreq.ClusterInstallRequest, string) (*coreentity.Request, error)
	BuildComponentList(*webreq.ClusterInstallRequest, string) ([]coreentity.ComponentResource, error)
}

// BaseClusterConfigBuilder 基础构建器
type BaseClusterConfigBuilder struct{}

// BuildConfig 构建集群配置
func (b *BaseClusterConfigBuilder) BuildConfig(installRequest *webreq.ClusterInstallRequest) (
	*coreentity.Request,
	error,
) {
	storageAddonVersion, serviceVersion, err := parseInstallVersion(installRequest)
	if err != nil {
		slog.Error("failed to parse install version", "installRequest", installRequest, "err", err)
		return nil, err
	}
	clusterConfig, err := b.BuildBasicConfig(installRequest, storageAddonVersion)
	if err != nil {
		slog.Error("failed to build cluster config", "installRequest", installRequest, "err", err)
		return nil, err
	}
	componentList, err := b.BuildComponentList(installRequest, serviceVersion)
	if err != nil {
		slog.Error("failed to build component list", "installRequest", installRequest, "err", err)
		return nil, err
	}
	clusterConfig.ComponentList = componentList
	return clusterConfig, nil
}

// BuildBasicConfig 构建基础配置信息
func (b *BaseClusterConfigBuilder) BuildBasicConfig(
	installRequest *webreq.ClusterInstallRequest,
	storageAddonVersion string,
) (
	*coreentity.Request,
	error) {
	return buildBasicClusterConfig(installRequest, storageAddonVersion)
}

// BuildComponentList 构建组件配置列表
func (b *BaseClusterConfigBuilder) BuildComponentList(
	installRequest *webreq.ClusterInstallRequest,
	serviceVersion string,
) (
	[]coreentity.ComponentResource,
	error,
) {
	componentList := make([]coreentity.ComponentResource, 0, len(installRequest.ResourceConfig.ComponentList))
	for _, component := range installRequest.ResourceConfig.ComponentList {
		componentResource := buildComponentResource(component, serviceVersion)
		componentResource.VolumeClaimTemplates = &coreentity.VolumeClaimTemplates{
			AccessModes:      []string{"ReadWriteOnce"},
			StorageClassName: "cbs",
			VolumeMode:       "Filesystem",
			Storage:          component.Storage,
		}
		componentList = append(componentList, componentResource)
	}
	return componentList, nil
}

// VMClusterConfigBuilder vm 集群配置构建器
type VMClusterConfigBuilder struct {
}

// BuildConfig 构建 config
func (v *VMClusterConfigBuilder) BuildConfig(installRequest *webreq.ClusterInstallRequest) (
	*coreentity.Request,
	error,
) {
	storageAddonVersion, serviceVersion, err := parseInstallVersion(installRequest)
	if err != nil {
		slog.Error("failed to parse install version", "installRequest", installRequest, "err", err)
		return nil, err
	}
	clusterConfig, err := v.BuildBasicConfig(installRequest, storageAddonVersion)
	if err != nil {
		slog.Error("failed to build cluster config", "installRequest", installRequest, "err", err)
		return nil, err
	}
	componentList, err := v.BuildComponentList(installRequest, serviceVersion)
	if err != nil {
		slog.Error("failed to build component list", "installRequest", installRequest, "err", err)
		return nil, err
	}
	clusterConfig.ComponentList = componentList
	return clusterConfig, nil
}

// BuildBasicConfig 构建基础配置信息
func (v *VMClusterConfigBuilder) BuildBasicConfig(
	request *webreq.ClusterInstallRequest,
	storageAddonVersion string,
) (*coreentity.Request, error) {
	return buildBasicClusterConfig(request, storageAddonVersion)
}

// BuildComponentList 构建组件配置列表
func (v *VMClusterConfigBuilder) BuildComponentList(
	installRequest *webreq.ClusterInstallRequest,
	serviceVersion string,
) ([]coreentity.ComponentResource, error) {
	switch installRequest.ResourceConfig.TopoName {
	case coreconst.VMClusterTopo:
		componentList, err := v.buildComponentsInCluster(installRequest, serviceVersion)
		if err != nil {
			slog.Error("failed to build component list", "installRequest", installRequest, "err", err)
			return nil, err
		}
		return componentList, nil
	case coreconst.VMQueryTopo:
		componentList, err := v.buildComponentsInQuery(installRequest, serviceVersion)
		if err != nil {
			return nil, err
		}
		return componentList, nil
	default:
		return nil, fmt.Errorf("unknown topo name %v", installRequest.ResourceConfig.TopoName)
	}
}

// buildComponentsInQuery VM 查询模式构建组件列表
func (v *VMClusterConfigBuilder) buildComponentsInQuery(
	installRequest *webreq.ClusterInstallRequest,
	serviceVersion string,
) ([]coreentity.ComponentResource, error) {
	var componentList []coreentity.ComponentResource
	for _, component := range installRequest.ResourceConfig.ComponentList {
		if component.ComponentName == coreconst.VMSelect {
			componentResource := buildComponentResource(component, serviceVersion)
			componentResource.Env = map[string]interface{}{
				"EXTRA_ARGS": map[string]string{
					"storageNode": component.StorageNodes,
				},
			}
			componentList = append(componentList, componentResource)
			break
		}
	}
	if len(componentList) == 0 {
		return nil, fmt.Errorf("failed to find the vmselect component")
	}
	return componentList, nil
}

// buildComponentsInCluster VM 集群模式构建组件配置列表
func (v *VMClusterConfigBuilder) buildComponentsInCluster(
	installRequest *webreq.ClusterInstallRequest,
	serviceVersion string,
) ([]coreentity.ComponentResource, error) {
	componentList := make([]coreentity.ComponentResource, 0, len(installRequest.ResourceConfig.ComponentList))
	for _, component := range installRequest.ResourceConfig.ComponentList {
		componentResource := buildComponentResource(component, serviceVersion)
		if component.ComponentName == coreconst.VMStorage {
			componentResource.VolumeClaimTemplates = &coreentity.VolumeClaimTemplates{
				AccessModes:      []string{"ReadWriteOnce"},
				StorageClassName: "cbs",
				VolumeMode:       "Filesystem",
				Storage:          component.Storage,
			}
		}
		componentList = append(componentList, componentResource)
	}
	return componentList, nil
}

// buildComponentResource 构建 ComponentResource
func buildComponentResource(component webreq.Component, serviceVersion string) coreentity.ComponentResource {
	componentResource := coreentity.ComponentResource{
		ComponentName: component.ComponentName,
		Replicas:      component.Replicas,
		Version:       serviceVersion,
		Request: &coreentity.Resource{
			CPU:    component.RequestCPU,
			Memory: component.RequestMemory,
		},
		Limit: &coreentity.Resource{
			CPU:    component.RequestCPU,
			Memory: component.RequestMemory,
		},
	}
	return componentResource
}

var ClusterConfBuilderFactory = &ClusterConfigBuilderFactory{}

// ClusterConfigBuilderFactory 集群配置构建器工厂
type ClusterConfigBuilderFactory struct {
	builderMap map[string]ClusterConfigBuilder
}

// GetBuilder 获取 ClusterConfigBuilder
func (c *ClusterConfigBuilderFactory) GetBuilder(addonType string) ClusterConfigBuilder {
	builder, ok := c.builderMap[addonType]
	if !ok {
		return &BaseClusterConfigBuilder{}
	}
	return builder
}

func init() {
	ClusterConfBuilderFactory.builderMap = make(map[string]ClusterConfigBuilder)
	ClusterConfBuilderFactory.builderMap[coreconst.VM] = &VMClusterConfigBuilder{}
}

// parseInstallVersion 解析 addon version 和 service version
func parseInstallVersion(install *webreq.ClusterInstallRequest) (string, string, error) {
	versions := install.ResourceConfig.Version
	if len(versions) != 2 {
		return "", "", errors.NewK8sDbsError(
			errors.CreateClusterError,
			fmt.Errorf("invalid version configuration: expected exactly 2 versions, got %d", len(versions)),
		)
	}
	storageAddonVersion := versions[0]
	serviceVersion := versions[1]
	return storageAddonVersion, serviceVersion, nil
}

// getNameSpace 获取命名空间
func getNameSpace(install *webreq.ClusterInstallRequest) string {
	return install.BasicInfo.StorageAddonType + "-" + strconv.FormatUint(install.BasicInfo.BkBizID, 10)
}

// buildBasicClusterConfig 构建基础配置信息
func buildBasicClusterConfig(installRequest *webreq.ClusterInstallRequest, addonVersion string) (
	*coreentity.Request,
	error,
) {
	clusterName := installRequest.BasicInfo.ClusterName
	if err := validateClusterName(clusterName); err != nil {
		return nil, err
	}
	clusterConfig := &coreentity.Request{
		K8sClusterName: installRequest.DeploymentEnv.K8sClusterName,
		BkBizID:        installRequest.BasicInfo.BkBizID,
		BkBizName:      installRequest.BasicInfo.BkBizName,
		BkAppAbbr:      installRequest.BasicInfo.BkAppAbbr,
		Tags:           installRequest.BasicInfo.Tags,
		Description:    installRequest.BasicInfo.Description,
		Metadata: coreentity.Metadata{
			Namespace:           getNameSpace(installRequest),
			ClusterName:         installRequest.BasicInfo.ClusterName,
			ClusterAlias:        installRequest.BasicInfo.ClusterAlias,
			StorageAddonType:    installRequest.BasicInfo.StorageAddonType,
			StorageAddonVersion: addonVersion,
			AddonClusterVersion: addonVersion,
			Labels:              installRequest.AdvancedSettings.Labels,
		},
		Spec: coreentity.Spec{
			TopoName:          installRequest.ResourceConfig.TopoName,
			TerminationPolicy: installRequest.AdvancedSettings.TerminationPolicy,
		},
		BKAuth: installRequest.BKAuth,
	}
	return clusterConfig, nil
}
