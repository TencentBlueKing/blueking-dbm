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

package tests

import (
	coreconst "k8s-dbs/core/constant"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestUnmarshalTextSuccess 测试 TerminationPolicy 正常 Unmarshal
func TestUnmarshalTextSuccess(t *testing.T) {
	testCases := []struct {
		name   string
		input  string
		expect coreconst.TerminationPolicy
	}{
		{"DoNotTerminate", "DoNotTerminate", coreconst.DoNotTerminate},
		{"Halt", "Halt", coreconst.Halt},
		{"Delete", "Delete", coreconst.Delete},
		{"WipeOut", "WipeOut", coreconst.WipeOut},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			var tp coreconst.TerminationPolicy
			err := tp.UnmarshalText([]byte(tc.input))
			assert.NoError(t, err)
			assert.Equal(t, tc.expect, tp)
		})
	}
}

// TestUnmarshalTextFailure 测试 TerminationPolicy 异常 UnmarshalText
func TestUnmarshalTextFailure(t *testing.T) {
	invalidInputs := []string{"", "del", "delete"}
	for _, i := range invalidInputs {
		var tp coreconst.TerminationPolicy
		err := tp.UnmarshalText([]byte(i))
		assert.Error(t, err)
	}
}
