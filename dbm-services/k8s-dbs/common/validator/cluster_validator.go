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

package validator

import (
	"fmt"
	"log"
	"regexp"
	"sync"

	"github.com/gin-gonic/gin/binding"
	"github.com/go-playground/validator/v10"
	"k8s.io/apimachinery/pkg/api/resource"
)

var clusterRegisterOnce sync.Once

const (
	maxReleaseNameLen = 53
	releaseNameRegex  = `^[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*$`
)

var (
	regex          = regexp.MustCompile(releaseNameRegex)
	quantityRanges = map[string]struct{ min, max resource.Quantity }{
		"cpu":     {resource.MustParse("1"), resource.MustParse("48")},
		"memory":  {resource.MustParse("1Gi"), resource.MustParse("128Gi")},
		"storage": {resource.MustParse("100Gi"), resource.MustParse("100000Gi")},
	}
)

func validateQuantity(fl validator.FieldLevel, resType string) bool {
	q := fl.Field().Interface().(resource.Quantity)
	r := quantityRanges[resType]
	return q.Cmp(r.min) >= 0 && q.Cmp(r.max) <= 0
}

// ValidateK8sReleaseName 检查 k8s release name 格式
func ValidateK8sReleaseName(fl validator.FieldLevel) bool {
	name := fl.Field().String()
	return len(name) <= maxReleaseNameLen && regex.MatchString(name)
}

// ValidateCPUQuantity 检查 CPU 配额（1core～48core）
func ValidateCPUQuantity(fl validator.FieldLevel) bool { return validateQuantity(fl, "cpu") }

// ValidateMemoryQuantity 检查内存配额（1GB～128GB）
func ValidateMemoryQuantity(fl validator.FieldLevel) bool { return validateQuantity(fl, "memory") }

// ValidateStorageQuantity 检查存储配额（1GB～100000GB）
func ValidateStorageQuantity(fl validator.FieldLevel) bool { return validateQuantity(fl, "storage") }

// ClusterValidatorMap cluster 校验器 Map
var ClusterValidatorMap = map[string]func(fl validator.FieldLevel) bool{
	"k8sReleaseName":  ValidateK8sReleaseName,
	"cpuQuantity":     ValidateCPUQuantity,
	"memoryQuantity":  ValidateMemoryQuantity,
	"storageQuantity": ValidateStorageQuantity,
}

// RegisterClusterValidators 注册校验器
func RegisterClusterValidators(v *validator.Validate) error {
	for tag, fun := range ClusterValidatorMap {
		if err := v.RegisterValidation(tag, fun); err != nil {
			return fmt.Errorf("failed to register validator %s: %w", tag, err)
		}
	}
	return nil
}

func init() {
	clusterRegisterOnce.Do(func() {
		if v, ok := binding.Validator.Engine().(*validator.Validate); ok {
			if err := RegisterClusterValidators(v); err != nil {
				log.Printf("Failed to register validators: %v", err)
			}
		}
	})
}
