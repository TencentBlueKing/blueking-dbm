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

package componentenv

import (
	coreconst "k8s-dbs/core/constant"
	coreentity "k8s-dbs/core/entity"
	coreutil "k8s-dbs/core/util"
	"log/slog"
)

// SurrealEnvInjector 为 SurrealDB 组件补齐 USER 和 PASS 环境变量。
// 取值优先级：用户传入值 > existing env > 默认值 / 新生成。
type SurrealEnvInjector struct{}

// Inject 实现 EnvInjector。
func (s *SurrealEnvInjector) Inject(
	request *coreentity.Request,
	existingEnvByComp map[string]map[string]any,
) error {
	if request == nil {
		return nil
	}
	for i := range request.ComponentList {
		comp := &request.ComponentList[i]
		if comp.ComponentName != coreconst.SurrealDB {
			continue
		}
		if comp.Env == nil {
			comp.Env = make(map[string]any)
		}
		s.ensureUser(comp, existingEnvByComp)
		if err := s.ensurePass(comp, existingEnvByComp); err != nil {
			return err
		}
	}
	return nil
}

func (s *SurrealEnvInjector) ensureUser(
	comp *coreentity.ComponentResource,
	existingEnvByComp map[string]map[string]any,
) {
	if v, ok := comp.Env[coreconst.SurrealEnvUser]; ok && !isEmptyEnvValue(v) {
		return
	}
	if existingEnvByComp != nil {
		if envMap, ok := existingEnvByComp[comp.ComponentName]; ok && envMap != nil {
			if v, ok := envMap[coreconst.SurrealEnvUser]; ok && !isEmptyEnvValue(v) {
				comp.Env[coreconst.SurrealEnvUser] = v
				return
			}
		}
	}
	comp.Env[coreconst.SurrealEnvUser] = coreconst.SurrealDefaultUser
}

func (s *SurrealEnvInjector) ensurePass(
	comp *coreentity.ComponentResource,
	existingEnvByComp map[string]map[string]any,
) error {
	if v, ok := comp.Env[coreconst.SurrealEnvPass]; ok && !isEmptyEnvValue(v) {
		return nil
	}
	if existingEnvByComp != nil {
		if envMap, ok := existingEnvByComp[comp.ComponentName]; ok && envMap != nil {
			if v, ok := envMap[coreconst.SurrealEnvPass]; ok && !isEmptyEnvValue(v) {
				comp.Env[coreconst.SurrealEnvPass] = v
				return nil
			}
		}
	}
	pass, err := coreutil.GenerateBase64RandKey(coreconst.SurrealPassRandBytes)
	if err != nil {
		return err
	}
	comp.Env[coreconst.SurrealEnvPass] = pass
	slog.Info("surreal injector: generated env",
		"component", comp.ComponentName, "envKey", coreconst.SurrealEnvPass)
	return nil
}

func init() {
	Registry.InjectorMap[coreconst.Surreal] = &SurrealEnvInjector{}
}
