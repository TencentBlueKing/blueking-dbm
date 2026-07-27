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
	"log"
	"sync"

	coreentity "k8s-dbs/core/entity"

	"github.com/gin-gonic/gin/binding"
	"github.com/go-playground/validator/v10"
)

const (
	// TagCPURequestLteLimit CPU request 必须 ≤ limit 的校验 tag
	TagCPURequestLteLimit = "cpuRequestLteLimit"
	// TagMemoryRequestLteLimit Memory request 必须 ≤ limit 的校验 tag
	TagMemoryRequestLteLimit = "memoryRequestLteLimit"
)

// TagMessages 提供自定义校验 tag 的中文错误信息兜底映射
// 当字段本身未定义 msg tag（或 msg tag 不适用于当前触发的 tag）时，
// 上层错误响应模块可通过此映射获取更精确的消息。
// 后续新增自定义 tag 时可继续向本 map 追加。
var TagMessages = map[string]string{
	TagCPURequestLteLimit:    "cpu request 不能大于 limit",
	TagMemoryRequestLteLimit: "memory request 不能大于 limit",
}

var resourceQuotaRegisterOnce sync.Once

// ValidateResourceQuotaStruct 校验 ResourceQuota 的一致性：
//  1. 当 Request.CPU 与 Limit.CPU 均非零且 Request.CPU > Limit.CPU 时报错
//  2. 当 Request.Memory 与 Limit.Memory 均非零且 Request.Memory > Limit.Memory 时报错
//
// 若任意一方为零值，则跳过对应项一致性校验（与 `omitempty` 语义保持一致，
// 非零校验由 provider 层现有 validateResourceQuota 负责）。
func ValidateResourceQuotaStruct(sl validator.StructLevel) {
	rq, ok := sl.Current().Interface().(coreentity.ResourceQuota)
	if !ok {
		return
	}

	// CPU 一致性校验
	if !rq.Request.CPU.IsZero() && !rq.Limit.CPU.IsZero() &&
		rq.Request.CPU.Cmp(rq.Limit.CPU) > 0 {
		sl.ReportError(
			rq.Request.CPU,
			"Request.CPU",
			"Request.CPU",
			TagCPURequestLteLimit,
			"",
		)
	}

	// Memory 一致性校验
	if !rq.Request.Memory.IsZero() && !rq.Limit.Memory.IsZero() &&
		rq.Request.Memory.Cmp(rq.Limit.Memory) > 0 {
		sl.ReportError(
			rq.Request.Memory,
			"Request.Memory",
			"Request.Memory",
			TagMemoryRequestLteLimit,
			"",
		)
	}
}

// ValidateComponentResourceStruct 校验 ComponentResource 的资源一致性：
//  1. 当 Request 与 Limit 均非空，且 Request.CPU > Limit.CPU 时报错
//  2. 当 Request 与 Limit 均非空，且 Request.Memory > Limit.Memory 时报错
//
// 若 Request 或 Limit 任一为空指针，则跳过一致性校验（与 `omitempty` 语义保持一致）。
// CreateCluster 请求链路（entity.Request -> Spec -> []ComponentResource）走的是此类型，
// 与 ResourceQuota 是两种不同结构，需单独注册结构体级校验。
func ValidateComponentResourceStruct(sl validator.StructLevel) {
	cr, ok := sl.Current().Interface().(coreentity.ComponentResource)
	if !ok {
		return
	}
	req, lim := cr.Request, cr.Limit
	if req == nil || lim == nil {
		return
	}

	// CPU 一致性校验
	if !req.CPU.IsZero() && !lim.CPU.IsZero() && req.CPU.Cmp(lim.CPU) > 0 {
		sl.ReportError(
			req.CPU,
			"Request.CPU",
			"Request.CPU",
			TagCPURequestLteLimit,
			"",
		)
	}

	// Memory 一致性校验
	if !req.Memory.IsZero() && !lim.Memory.IsZero() && req.Memory.Cmp(lim.Memory) > 0 {
		sl.ReportError(
			req.Memory,
			"Request.Memory",
			"Request.Memory",
			TagMemoryRequestLteLimit,
			"",
		)
	}
}

// RegisterResourceQuotaValidators 将 ResourceQuota 相关的结构体级校验器注册到给定 validator 实例
func RegisterResourceQuotaValidators(v *validator.Validate) {
	v.RegisterStructValidation(ValidateResourceQuotaStruct, coreentity.ResourceQuota{})
	v.RegisterStructValidation(ValidateComponentResourceStruct, coreentity.ComponentResource{})
}

func init() {
	resourceQuotaRegisterOnce.Do(func() {
		v, ok := binding.Validator.Engine().(*validator.Validate)
		if !ok {
			log.Printf("Failed to obtain validator engine for ResourceQuota validators")
			return
		}
		RegisterResourceQuotaValidators(v)
	})
}
