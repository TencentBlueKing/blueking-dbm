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
	"fmt"
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	coreutil "k8s-dbs/core/util"
	webreq "k8s-dbs/dataweb/vo/request"
	"k8s-dbs/errors"

	"regexp"
	"strings"
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

// buildComponentResource 构建 ComponentResource
func buildComponentResource(component webreq.Component, serviceVersion string) coreentity.ComponentResource {
	componentResource := coreentity.ComponentResource{
		ComponentName: component.ComponentName,
		Replicas:      component.Replicas,
		Version:       &serviceVersion,
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

// parseCommandLineArgs 将命令行参数字符串解析为map
func parseCommandLineArgs(input string) map[string]interface{} {
	// 创建一个map用于存储结果
	result := make(map[string]interface{})

	// 按空格分割字符串，得到各个参数
	params := strings.Fields(input)

	// 遍历每个参数
	for _, param := range params {
		// 去除开头的"--"
		keyValue := strings.TrimPrefix(param, "--")

		// 按"="分割为键和值
		parts := strings.SplitN(keyValue, "=", 2)
		if len(parts) == 2 {
			key := parts[0]
			value := parts[1]
			result[key] = value
		}
	}

	return result
}

var ClusterConfBuilderFactory = &ClusterConfigBuilderFactory{}

// ClusterConfigBuilderFactory 集群配置构建器工厂
type ClusterConfigBuilderFactory struct {
	builderMap map[coreconst.StorageAddonType]ClusterConfigBuilder
}

// GetBuilder 获取 ClusterConfigBuilder
func (c *ClusterConfigBuilderFactory) GetBuilder(addonType coreconst.StorageAddonType) ClusterConfigBuilder {
	builder, ok := c.builderMap[addonType]
	if !ok {
		return &BaseClusterConfigBuilder{}
	}
	return builder
}

func init() {
	ClusterConfBuilderFactory.builderMap = make(map[coreconst.StorageAddonType]ClusterConfigBuilder)
	ClusterConfBuilderFactory.builderMap[coreconst.Victoriametrics] = &VMClusterConfigBuilder{}
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
	namespace := install.BasicInfo.Namespace
	if strings.TrimSpace(namespace) != "" {
		return namespace
	}
	return coreutil.GetDefaultNameSpace(
		install.BasicInfo.BkBizID,
		install.BasicInfo.BkAppAbbr,
		install.BasicInfo.StorageAddonType,
	)
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
