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
	"encoding/base64"
	"k8s-dbs/core/util"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestGenerateBase64RandKey_Len32 验证 n=32 时返回 Base64 长度为 44 且解码后字节数等于 32。
func TestGenerateBase64RandKey_Len32(t *testing.T) {
	key, err := util.GenerateBase64RandKey(32)
	assert.NoError(t, err)
	assert.Equal(t, 44, len(key), "32 字节随机经 Base64 标准编码后长度应为 44")

	decoded, err := base64.StdEncoding.DecodeString(key)
	assert.NoError(t, err)
	assert.Equal(t, 32, len(decoded), "解码后原始字节数应等于入参 nBytes")
}

// TestGenerateBase64RandKey_Randomness 两次调用结果不同（随机性）。
func TestGenerateBase64RandKey_Randomness(t *testing.T) {
	k1, err := util.GenerateBase64RandKey(32)
	assert.NoError(t, err)
	k2, err := util.GenerateBase64RandKey(32)
	assert.NoError(t, err)
	assert.NotEqual(t, k1, k2, "两次独立调用应返回不同的随机密钥")
}

// TestGenerateBase64RandKey_InvalidInput 入参 <= 0 应返回错误。
func TestGenerateBase64RandKey_InvalidInput(t *testing.T) {
	cases := []int{0, -1, -32}
	for _, n := range cases {
		key, err := util.GenerateBase64RandKey(n)
		assert.Error(t, err, "nBytes=%d 应返回错误", n)
		assert.Equal(t, "", key)
	}
}

// TestGenerateBase64RandKey_VariableBytes 不同字节数均能正确工作。
func TestGenerateBase64RandKey_VariableBytes(t *testing.T) {
	cases := []int{1, 16, 24, 32, 64}
	for _, n := range cases {
		key, err := util.GenerateBase64RandKey(n)
		assert.NoError(t, err)
		decoded, err := base64.StdEncoding.DecodeString(key)
		assert.NoError(t, err)
		assert.Equal(t, n, len(decoded), "解码后字节数应等于入参 nBytes=%d", n)
	}
}
