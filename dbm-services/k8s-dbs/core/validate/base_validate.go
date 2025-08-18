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
	coreentity "k8s-dbs/core/entity"
	"regexp"
)

const TimeRegexp = `^[0-9]+(ms|[smhdy])(|i)$`
const BoolRegexp = `^(true|false)$`
const NumberRegexp = `^\d+$`
const StorageUnitRegexp = `^[0-9]+[KMGTP]B$`

// 校验接口
type Validator interface {
	Validate(request *coreentity.Request) error
}

// 校验规则
type ValidationRules map[string]*regexp.Regexp

// 校验器工厂
func ValidatorFactory(storageType string) (Validator, error) {
	switch storageType {
	case "victoriametrics":
		return initVictoriaMetricsValidator(), nil
		// case "surreal":
		//     return surreal, nil
	default:
		return nil, nil
	}
}

func Params(request *coreentity.Request) error {
	validator, err := ValidatorFactory(request.StorageAddonType)
	if err != nil {
		return err
	}

	if validator == nil {
		return nil
	}
	return validator.Validate(request)
}
