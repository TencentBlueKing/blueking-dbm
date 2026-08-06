/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package precheck

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"unicode/utf8"

	"dbm-services/mysql/db-simulation/app/sqlserver"
)

// 常见文件 BOM 定义
var (
	bomUTF8    = []byte{0xEF, 0xBB, 0xBF}
	bomUTF16LE = []byte{0xFF, 0xFE}
	bomUTF16BE = []byte{0xFE, 0xFF}
	bomUTF32LE = []byte{0xFF, 0xFE, 0x00, 0x00}
	bomUTF32BE = []byte{0x00, 0x00, 0xFE, 0xFF}
)

// 编码字符串常量
const (
	encodingUTF8BOM               = "utf-8-bom"
	encodingASCIIOnly             = "ascii-only"
	encodingUTF8NoBOMWithNonASCII = "utf-8-no-bom-with-non-ascii"
	encodingUTF16LEBOM            = "utf-16-le-bom"
	encodingUTF16BEBOM            = "utf-16-be-bom"
	encodingUTF32LEBOM            = "utf-32-le-bom"
	encodingUTF32BEBOM            = "utf-32-be-bom"
	encodingUnknown               = "unknown"
)

const (
	nonASCIIUTF8Message           = "文件编码校验失败：当前文件为无 BOM 的 UTF-8，且包含非 ASCII 字符。该格式在 Windows/sqlcmd 跨语言环境下可能被错误解析。请将文件转换为 UTF-8 with BOM 后重新提交。仅纯 ASCII 文件允许不带 BOM。若脚本中包含非 ASCII 字符串字面量，建议优先使用 N'...' 表示 Unicode 文本。"
	nonUTF8Message                = "文件编码校验失败：当前文件不是 UTF-8，且不带 BOM。该文件可能使用本地 ANSI/代码页编码，并可能在 Windows/sqlcmd 跨语言环境下被错误解析。请将文件转换为 UTF-8 with BOM 后重新提交。仅纯 ASCII 文件允许不带 BOM。"
	unsupportedEncodingMessageFmt = "文件编码校验失败：检测到不支持的编码 %s。请将文件转换为 UTF-8 with BOM 后重新提交。仅纯 ASCII 文件允许不带 BOM。"
)

// EncodingChecker 文件编码检查器。
// 允许以下两类文件通过：
//   - UTF-8 with BOM
//   - 无 BOM 但全文仅包含 ASCII 字节的文件
//
// 其余无 BOM 且包含非 ASCII 的 UTF-8 文件、以及非 UTF-8 文件一律拒绝。
type EncodingChecker struct{}

// NewEncodingChecker 创建一个编码检查器实例
func NewEncodingChecker() *EncodingChecker {
	return &EncodingChecker{}
}

// init 自注册到全局检查器注册表。
// 后续新增其它检查器时，只需在各自文件的 init() 中执行同样的 Register 调用即可，
// handler / RunAll 主代码无需任何修改。
func init() {
	Register(NewEncodingChecker())
}

// Name 返回检查器名称
func (e *EncodingChecker) Name() string {
	return "encoding"
}

// Check 检查给定文件是否符合允许的编码规则。
func (e *EncodingChecker) Check(filePath string) (sqlserver.FileCheckResult, error) {
	fileName := filepath.Base(filePath)
	result := sqlserver.FileCheckResult{
		FileName: fileName,
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		return result, fmt.Errorf("read file %s failed: %w", filePath, err)
	}

	encoding := detectEncoding(content)
	result.Encoding = encoding

	switch encoding {
	case encodingUTF8BOM, encodingASCIIOnly:
		result.Status = sqlserver.FileCheckPass
		return result, nil
	case encodingUTF8NoBOMWithNonASCII:
		result.Status = sqlserver.FileCheckFail
		result.Message = nonASCIIUTF8Message
		return result, nil
	case encodingUnknown:
		result.Status = sqlserver.FileCheckFail
		result.Message = nonUTF8Message
		return result, nil
	default:
		result.Status = sqlserver.FileCheckFail
		result.Message = fmt.Sprintf(unsupportedEncodingMessageFmt, encoding)
		return result, nil
	}
}

// detectEncoding 基于 BOM 与全文字节内容探测编码类型。
// 注意：UTF-32 的 BOM (FF FE 00 00) 前两字节和 UTF-16 LE (FF FE) 相同，
// 因此必须优先判断更长的 UTF-32 BOM。
func detectEncoding(content []byte) string {
	switch {
	case bytes.HasPrefix(content, bomUTF8):
		return encodingUTF8BOM
	case bytes.HasPrefix(content, bomUTF32LE):
		return encodingUTF32LEBOM
	case bytes.HasPrefix(content, bomUTF32BE):
		return encodingUTF32BEBOM
	case bytes.HasPrefix(content, bomUTF16LE):
		return encodingUTF16LEBOM
	case bytes.HasPrefix(content, bomUTF16BE):
		return encodingUTF16BEBOM
	case isASCIIOnly(content):
		return encodingASCIIOnly
	case utf8.Valid(content):
		return encodingUTF8NoBOMWithNonASCII
	default:
		return encodingUnknown
	}
}

func isASCIIOnly(content []byte) bool {
	for _, b := range content {
		if b >= utf8.RuneSelf {
			return false
		}
	}
	return true
}
