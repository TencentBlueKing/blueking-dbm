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
	"crypto/rand"
	"encoding/base64"
	"fmt"
)

// GenerateBase64RandKey 生成等价于 `openssl rand -base64 N` 的 Base64 随机密钥。
//
// 行为：读取 nBytes 字节的密码学安全随机数（crypto/rand），再使用 base64.StdEncoding 编码后返回。
// 常见用法：GenerateBase64RandKey(32) 产生长度为 44 的字符串（32 字节原始随机 → Base64）。
//
// 参数：
//   - nBytes: 原始随机字节数，必须 > 0。
//
// 返回：
//   - string: Base64 标准编码后的随机密钥。
//   - error: nBytes <= 0 时返回参数错误；crypto/rand 读取失败时返回包装后的错误。
func GenerateBase64RandKey(nBytes int) (string, error) {
	if nBytes <= 0 {
		return "", fmt.Errorf("GenerateBase64RandKey: nBytes must be > 0, got %d", nBytes)
	}
	buf := make([]byte, nBytes)
	if _, err := rand.Read(buf); err != nil {
		return "", fmt.Errorf("GenerateBase64RandKey: read crypto/rand failed: %w", err)
	}
	return base64.StdEncoding.EncodeToString(buf), nil
}
