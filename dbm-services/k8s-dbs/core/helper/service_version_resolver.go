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

package helper

import (
	coreentity "k8s-dbs/core/entity"
)

// ServiceVersionResolver 解析引擎版本
type ServiceVersionResolver interface {
	Resolve(componentList []coreentity.ComponentResource) (string, error)
}

// BaseServiceVersionResolver 基础解析器
type BaseServiceVersionResolver struct {
}

// Resolve 通用解析方法
func (b *BaseServiceVersionResolver) Resolve(componentList []coreentity.ComponentResource) (string, error) {
	if len(componentList) == 0 {
		return "", nil
	}
	component := componentList[0]
	return component.Version, nil
}

// SurrealDBServiceVersionResolver SurrealDB 解析器
type SurrealDBServiceVersionResolver struct {
}

// Resolve SurrealDB 解析方法
func (v *SurrealDBServiceVersionResolver) Resolve(componentList []coreentity.ComponentResource) (string, error) {
	if componentList == nil {
		return "", nil
	}
	for _, component := range componentList {
		if component.ComponentName == "surreal" {
			return component.Version, nil
		}
	}
	return "", nil
}

var (
	SVRFactory = &ServiceVersionResolverFactory{}
)

// ServiceVersionResolverFactory ServiceVersionResolver factory
type ServiceVersionResolverFactory struct {
	ResolverMap map[string]ServiceVersionResolver
}

// GetResolver 获取 ServiceVersionResolver
func (s *ServiceVersionResolverFactory) GetResolver(addonType string) ServiceVersionResolver {
	var resolver ServiceVersionResolver
	resolver, ok := s.ResolverMap[addonType]
	if !ok {
		return &BaseServiceVersionResolver{}
	}
	return resolver
}

func init() {
	SVRFactory.ResolverMap = make(map[string]ServiceVersionResolver)
	SVRFactory.ResolverMap["base"] = &BaseServiceVersionResolver{}
	SVRFactory.ResolverMap["vm"] = &BaseServiceVersionResolver{}
	SVRFactory.ResolverMap["surreal"] = &SurrealDBServiceVersionResolver{}
}
