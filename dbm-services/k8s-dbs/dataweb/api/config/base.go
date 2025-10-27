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

package config

import (
	coreentity "k8s-dbs/core/entity"
	webreq "k8s-dbs/dataweb/vo/request"
	"log/slog"

	"github.com/jinzhu/copier"
)

// ClusterConfigBuilder 构建集群部署配置结构体
type ClusterConfigBuilder interface {
	BuildConfig(*webreq.ClusterInstallRequest) (*coreentity.Request, error)
	BuildBasicConfig(*webreq.ClusterInstallRequest, string) (*coreentity.Request, error)
	BuildComponentList(*webreq.ClusterInstallRequest, string) ([]coreentity.ComponentResource, error)
	BuildEnvConfig(request *webreq.ClusterUpdatedRequest) (*coreentity.Request, error)
	ParseEnvConfig(request *coreentity.ComponentDetail) (*webreq.ComponentDetail, error)
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

// BuildEnvConfig 构建env
func (b *BaseClusterConfigBuilder) BuildEnvConfig(request *webreq.ClusterUpdatedRequest) (*coreentity.Request, error) {
	for i, resource := range request.ComponentList {
		if resource.Config == nil {
			continue
		}
		request.ComponentList[i].Env = resource.Config
	}
	var result = &coreentity.Request{}
	err := copier.Copy(result, request)
	if err != nil {
		return nil, err
	}
	return result, nil
}

// ParseEnvConfig 解析Env
func (b *BaseClusterConfigBuilder) ParseEnvConfig(
	request *coreentity.ComponentDetail,
) (*webreq.ComponentDetail, error) {
	var result = &webreq.ComponentDetail{}
	err := copier.Copy(result, request)
	if err != nil {
		return nil, err
	}
	envMap := make(map[string]interface{})
	result.Config = envMap
	if request.Env != nil {
		for _, envVar := range request.Env {
			result.Config[envVar.Name] = envVar.Value
		}
	}
	return result, nil
}
