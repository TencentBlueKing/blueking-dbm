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

package util

import (
	"math"

	"k8s.io/apimachinery/pkg/api/resource"
)

// ConvertCPUToCores 将资源量转换为以 core 为单位的 float64 值
func ConvertCPUToCores(cpu *resource.Quantity) float64 {
	return float64(cpu.MilliValue()) / 1000.0
}

// ConvertMemoryToGB 将资源量转换为以 GB 为单位的 float64 值
func ConvertMemoryToGB(memory *resource.Quantity) float64 {
	return float64(memory.Value()) / (1024.0 * 1024.0 * 1024.0)
}

// RoundToDecimal 将浮点数四舍五入到指定小数位
func RoundToDecimal(val float64, decimalPlaces int) float64 {
	shift := math.Pow(10, float64(decimalPlaces))
	return math.Round(val*shift) / shift
}
