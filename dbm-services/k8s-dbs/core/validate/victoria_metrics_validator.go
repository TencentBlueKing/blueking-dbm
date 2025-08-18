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

package validate

import (
	"fmt"
	coreentity "k8s-dbs/core/entity"
	"regexp"
)

// vm校验器
type VictoriaMetricsValidator struct {
	rules ValidationRules
}

// 初始化VictoriaMetrics的校验规则
func initVictoriaMetricsValidator() *VictoriaMetricsValidator {
	return &VictoriaMetricsValidator{
		rules: ValidationRules{
			// 相关参数
			"cacheExpireDuration":                regexp.MustCompile(TimeRegexp),
			"dedup.minScrapeInterval":            regexp.MustCompile(TimeRegexp),
			"search.logSlowQueryDuration":        regexp.MustCompile(TimeRegexp),
			"search.queryStats.minQueryDuration": regexp.MustCompile(TimeRegexp),
			"memory.allowedPercent":              regexp.MustCompile(NumberRegexp),
			"search.maxUniqueTimeseries":         regexp.MustCompile(NumberRegexp),
			"search.maxSeriesPerAggrFunc":        regexp.MustCompile(NumberRegexp),
			"search.maxSamplesPerQuery":          regexp.MustCompile(NumberRegexp),
			"search.maxPointsPerTimeseries":      regexp.MustCompile(NumberRegexp),
			"search.maxSeries":                   regexp.MustCompile(NumberRegexp),
			"search.queryStats.lastQueriesCount": regexp.MustCompile(NumberRegexp),
			"search.maxConcurrentRequests":       regexp.MustCompile(NumberRegexp),
			"search.maxMemoryPerQuery":           regexp.MustCompile(StorageUnitRegexp),
			"search.logQueryMemoryUsage":         regexp.MustCompile(StorageUnitRegexp),
			"search.maxQueryLen":                 regexp.MustCompile(StorageUnitRegexp),
			"envflag.enable":                     regexp.MustCompile(BoolRegexp),
		},
	}
}

// 实现Validator接口
func (v *VictoriaMetricsValidator) Validate(request *coreentity.Request) error {
	// 校验每个组件
	for _, component := range request.ComponentList {
		if err := v.validateComponent(component); err != nil {
			return err
		}
	}

	return nil
}

// 校验Component
func (v *VictoriaMetricsValidator) validateComponent(component coreentity.ComponentResource) error {
	// 校验EXTRA_ARGS
	if component.Env["EXTRA_ARGS"] != nil {
		if extraArgsMap, ok := component.Env["EXTRA_ARGS"].(map[string]interface{}); ok {
			for key, value := range extraArgsMap {
				value := value.(string)
				if err := v.validateExtraArg(key, value, component.ComponentName); err != nil {
					return err
				}
			}
		}
	}

	return nil
}

func (v *VictoriaMetricsValidator) validateExtraArg(key, value, componentName string) error {
	rule, exists := v.rules[key]
	if !exists {
		return nil
	}

	if !rule.MatchString(value) {
		return fmt.Errorf("组件%s的参数%s值无效: %s",
			componentName, key, value)
	}

	return nil
}
