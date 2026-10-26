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

// QdrantEnvInjector 为 Qdrant 组件补齐 API Key 和 Read-Only API Key 环境变量。
// 取值优先级：用户传入值 > existing env > 新生成。
type QdrantEnvInjector struct{}

// Inject 实现 EnvInjector。
func (q *QdrantEnvInjector) Inject(
	request *coreentity.Request,
	existingEnvByComp map[string]map[string]any,
) error {
	if request == nil {
		return nil
	}
	for i := range request.ComponentList {
		comp := &request.ComponentList[i]
		if comp.Env == nil {
			comp.Env = make(map[string]any)
		}
		if err := q.ensureEnv(comp, existingEnvByComp, coreconst.QdrantEnvAPIKey); err != nil {
			return err
		}
		if err := q.ensureEnv(comp, existingEnvByComp, coreconst.QdrantEnvReadOnlyAPIKey); err != nil {
			return err
		}
	}
	return nil
}

func (q *QdrantEnvInjector) ensureEnv(
	comp *coreentity.ComponentResource,
	existingEnvByComp map[string]map[string]any,
	envKey string,
) error {
	if v, ok := comp.Env[envKey]; ok && !isEmptyEnvValue(v) {
		return nil
	}
	if existingEnvByComp != nil {
		if envMap, ok := existingEnvByComp[comp.ComponentName]; ok && envMap != nil {
			if v, ok := envMap[envKey]; ok && !isEmptyEnvValue(v) {
				comp.Env[envKey] = v
				return nil
			}
		}
	}
	key, err := coreutil.GenerateBase64RandKey(coreconst.QdrantAPIKeyRandBytes)
	if err != nil {
		return err
	}
	comp.Env[envKey] = key
	slog.Info("qdrant injector: generated env",
		"component", comp.ComponentName, "envKey", envKey)
	return nil
}

func isEmptyEnvValue(v any) bool {
	if v == nil {
		return true
	}
	if s, ok := v.(string); ok {
		return s == ""
	}
	return false
}

func init() {
	Registry.InjectorMap[coreconst.Qdrant] = &QdrantEnvInjector{}
}
