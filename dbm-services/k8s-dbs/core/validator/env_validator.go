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

// Package validator 提供环境变量参数验证功能
package validator

import (
	"fmt"
	"strconv"

	metaentity "k8s-dbs/metadata/entity"
	metaprovider "k8s-dbs/metadata/provider"
)

// EnvValidator 环境变量验证器
type EnvValidator struct {
	paramConfigProvider metaprovider.AddonParamConfigProvider
	addonProvider       metaprovider.K8sCrdStorageAddonProvider
}

// NewEnvValidator 创建验证器实例
func NewEnvValidator(
	paramConfigProvider metaprovider.AddonParamConfigProvider,
	addonProvider metaprovider.K8sCrdStorageAddonProvider,
) *EnvValidator {
	return &EnvValidator{
		paramConfigProvider: paramConfigProvider,
		addonProvider:       addonProvider,
	}
}

// ValidateVMEnv 验证 VictoriaMetrics 组件环境变量
// 参数：addonID(存储addon的ID), serviceVersion(服务版本), componentName(组件名), env(环境变量)
// 目前只验证 EXTRA_ARGS 模式
func (v *EnvValidator) ValidateVMEnv(
	addonID uint64,
	serviceVersion string,
	componentName string,
	env map[string]interface{},
) error {
	// 检查 addon 是否启用参数校验
	addon, err := v.addonProvider.FindStorageAddonByID(addonID)
	if err != nil {
		// 找不到 addon 或查询出错，跳过验证
		return nil
	}
	if !addon.EnableEnvValidation {
		// 未启用参数校验，跳过验证
		return nil
	}

	if env == nil {
		return nil
	}

	// 检查是否有 EXTRA_ARGS
	extraArgs, ok := env["EXTRA_ARGS"]
	if !ok {
		return nil
	}

	extraArgsMap, ok := extraArgs.(map[string]interface{})
	if !ok {
		return fmt.Errorf("EXTRA_ARGS must be a map")
	}

	// 如果 EXTRA_ARGS 为空，跳过验证
	if len(extraArgsMap) == 0 {
		return nil
	}

	// 从数据库获取该组件支持的参数配置
	supportedParams, err := v.paramConfigProvider.FindByVersionAndComponent(addonID, serviceVersion, componentName)
	if err != nil {
		return err
	}

	// 如果没有配置任何参数规则，跳过验证
	if len(supportedParams) == 0 {
		return nil
	}

	// 构建支持的参数 map
	supportedParamsMap := make(map[string]*metaentity.AddonParamConfigEntity)
	for _, param := range supportedParams {
		supportedParamsMap[param.ParamName] = param
	}

	// 验证每个 EXTRA_ARGS 参数
	for key, value := range extraArgsMap {
		paramConfig, exists := supportedParamsMap[key]
		if !exists {
			return fmt.Errorf("parameter '%s' is not supported for component '%s'", key, componentName)
		}

		if err := v.validateParamType(key, value, paramConfig.ParamType); err != nil {
			return err
		}
	}

	return nil
}

// validateParamType 验证参数类型
func (v *EnvValidator) validateParamType(
	paramName string,
	value interface{},
	paramType metaentity.ParamType,
) error {
	switch paramType {
	case metaentity.ParamTypeString:
		// string 类型不需要额外验证
		return nil
	case metaentity.ParamTypeInt:
		return v.validateInt(paramName, value)
	case metaentity.ParamTypeBool:
		return v.validateBool(paramName, value)
	default:
		// 未知类型当作 string 处理
		return nil
	}
}

// validateInt 验证整数类型
func (v *EnvValidator) validateInt(paramName string, value interface{}) error {
	switch val := value.(type) {
	case int, int32, int64, float64:
		return nil
	case string:
		if _, err := strconv.ParseInt(val, 10, 64); err != nil {
			return fmt.Errorf("parameter '%s' must be an integer, got '%s'", paramName, val)
		}
		return nil
	default:
		return fmt.Errorf("parameter '%s' must be an integer, got type %T", paramName, value)
	}
}

// validateBool 验证布尔类型
func (v *EnvValidator) validateBool(paramName string, value interface{}) error {
	switch val := value.(type) {
	case bool:
		return nil
	case string:
		if _, err := strconv.ParseBool(val); err != nil {
			return fmt.Errorf("parameter '%s' must be a boolean (true/false), got '%s'", paramName, val)
		}
		return nil
	default:
		return fmt.Errorf("parameter '%s' must be a boolean, got type %T", paramName, value)
	}
}
