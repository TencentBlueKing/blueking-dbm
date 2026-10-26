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

// Package serviceversion 按 addon 类型解析引擎的 serviceVersion。
package serviceversion

import (
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
)

// VersionResolver 服务版本解析器。
type VersionResolver interface {
	Resolve(componentList []coreentity.ComponentResource) (string, error)
}

// BaseVersionResolver 基础解析器，取第一个组件的 Version。
type BaseVersionResolver struct{}

// Resolve 通用解析方法。
func (b *BaseVersionResolver) Resolve(componentList []coreentity.ComponentResource) (string, error) {
	if len(componentList) == 0 {
		return "", nil
	}
	component := componentList[0]
	if component.Version == nil {
		return "", nil
	}
	return *component.Version, nil
}

// SurrealVersionResolver SurrealDB 专用解析器，取名为 surreal 的组件的 Version。
type SurrealVersionResolver struct{}

// Resolve SurrealDB 解析方法。
func (v *SurrealVersionResolver) Resolve(componentList []coreentity.ComponentResource) (string, error) {
	if componentList == nil {
		return "", nil
	}
	for _, component := range componentList {
		if component.ComponentName == "surreal" {
			if component.Version == nil {
				return "", nil
			}
			return *component.Version, nil
		}
	}
	return "", nil
}

// VersionResolverRegistry 服务版本解析器注册表。
type VersionResolverRegistry struct {
	ResolverMap map[coreconst.StorageAddonType]VersionResolver
}

// GetResolver 按 addonType 返回对应 VersionResolver，未注册时返回 BaseVersionResolver。
func (r *VersionResolverRegistry) GetResolver(addonType coreconst.StorageAddonType) VersionResolver {
	resolver, ok := r.ResolverMap[addonType]
	if !ok {
		return &BaseVersionResolver{}
	}
	return resolver
}

// Registry 全局服务版本解析器注册表单例。
var Registry = &VersionResolverRegistry{}

func init() {
	Registry.ResolverMap = make(map[coreconst.StorageAddonType]VersionResolver)
	Registry.ResolverMap[coreconst.Victoriametrics] = &BaseVersionResolver{}
	Registry.ResolverMap[coreconst.Surreal] = &SurrealVersionResolver{}
}
