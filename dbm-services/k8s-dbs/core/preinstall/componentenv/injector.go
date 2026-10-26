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

// Package componentenv 提供 helm install 前对组件环境变量的默认值注入能力。
package componentenv

import (
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
)

// EnvInjector 组件环境变量注入器。
type EnvInjector interface {
	Inject(request *coreentity.Request, existingEnvByComp map[string]map[string]any) error
}

// NoopEnvInjector 空实现，用于未注册的 addon。
type NoopEnvInjector struct{}

// Inject 不做任何处理。
func (n *NoopEnvInjector) Inject(_ *coreentity.Request, _ map[string]map[string]any) error {
	return nil
}

// EnvInjectorRegistry 环境变量注入器注册表。
type EnvInjectorRegistry struct {
	InjectorMap map[coreconst.StorageAddonType]EnvInjector
}

// GetInjector 按 addonType 返回对应 EnvInjector，未注册时返回 NoopEnvInjector。
func (r *EnvInjectorRegistry) GetInjector(addonType coreconst.StorageAddonType) EnvInjector {
	if injector, ok := r.InjectorMap[addonType]; ok {
		return injector
	}
	return &NoopEnvInjector{}
}

// Registry 全局注入器注册表单例。
var Registry = &EnvInjectorRegistry{}

func init() {
	Registry.InjectorMap = make(map[coreconst.StorageAddonType]EnvInjector)
}
