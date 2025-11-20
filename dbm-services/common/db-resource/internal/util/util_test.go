/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package util

import (
	"testing"
)

func TestCleanOsName(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		expected string
	}{
		// Tencent tlinux 系列
		{
			name:     "Tencent tlinux release 1.2 (Final)",
			input:    "Tencent tlinux release 1.2 (Final)",
			expected: "tliunx-1.2",
		},
		{
			name:     "Tencent tlinux release 2.2 (Final)",
			input:    "Tencent tlinux release 2.2 (Final)",
			expected: "tliunx-2.2",
		},
		{
			name:     "Tencent tlinux release 2.2 (tkernel3)",
			input:    "Tencent tlinux release 2.2 (tkernel3)",
			expected: "tliunx-2.2",
		},
		{
			name:     "Tencent tlinux release 2.6 (Final)",
			input:    "Tencent tlinux release 2.6 (Final)",
			expected: "tliunx-2.6",
		},
		{
			name:     "Tencent tlinux release 2.6 (tkernel4)",
			input:    "Tencent tlinux release 2.6 (tkernel4)",
			expected: "tliunx-2.6",
		},
		// TencentOS Server 系列
		{
			name:     "TencentOS Server 1.2",
			input:    "TencentOS Server 1.2",
			expected: "tliunx-1.2",
		},
		{
			name:     "TencentOS Server 1.2 (tkernel2)",
			input:    "TencentOS Server 1.2 (tkernel2)",
			expected: "tliunx-1.2",
		},
		{
			name:     "TencentOS Server 2.2",
			input:    "TencentOS Server 2.2",
			expected: "tliunx-2.2",
		},
		{
			name:     "TencentOS Server 2.2 (Final)",
			input:    "TencentOS Server 2.2 (Final)",
			expected: "tliunx-2.2",
		},
		{
			name:     "TencentOS Server 2.6",
			input:    "TencentOS Server 2.6",
			expected: "tliunx-2.6",
		},
		{
			name:     "TencentOS Server 2.6 (Final)",
			input:    "TencentOS Server 2.6 (Final)",
			expected: "tliunx-2.6",
		},
		{
			name:     "TencentOS Server 2.6 (TK4)",
			input:    "TencentOS Server 2.6 (TK4)",
			expected: "tliunx-2.6",
		},
		{
			name:     "TencentOS Server 3.2 (Final)",
			input:    "TencentOS Server 3.2 (Final)",
			expected: "tliunx-3.2",
		},
		{
			name:     "TencentOS Server 4 For Tencent",
			input:    "TencentOS Server 4 For Tencent",
			expected: "tliunx-4",
		},
		{
			name:     "TencentOS Server 4.2",
			input:    "TencentOS Server 4.2",
			expected: "tliunx-4.2",
		},
		{
			name:     "TencentOS Server 4.4",
			input:    "TencentOS Server 4.4",
			expected: "tliunx-4.4",
		},
		// 其他操作系统测试
		{
			name:     "Windows Server 2019",
			input:    "Windows Server 2019",
			expected: "WindowsServer2019",
		},
		{
			name:     "Windows Server 2022",
			input:    "Windows Server 2022",
			expected: "WindowsServer2022",
		},
		{
			name:     "Ubuntu 20.04 LTS",
			input:    "Ubuntu 20.04 LTS",
			expected: "Ubuntu 20.04 LTS",
		},
		{
			name:     "CentOS 7",
			input:    "CentOS 7",
			expected: "CentOS 7",
		},
		// 边界情况测试
		{
			name:     "空字符串",
			input:    "",
			expected: "",
		},
		{
			name:     "带前后空格的Tencent tlinux",
			input:    "  Tencent tlinux release 2.6 (Final)  ",
			expected: "tliunx-2.6",
		},
		{
			name:     "小写tencent tlinux",
			input:    "tencent tlinux release 2.6 (final)",
			expected: "tliunx-2.6",
		},
		{
			name:     "小写tencentos server",
			input:    "tencentos server 2.6 (final)",
			expected: "tliunx-2.6",
		},
		{
			name:     "小写windows server",
			input:    "windows server 2019",
			expected: "windowsserver2019",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := CleanOsName(tt.input)
			if result != tt.expected {
				t.Errorf("CleanOsName(%q) = %q, 期望 %q", tt.input, result, tt.expected)
			}
		})
	}
}
