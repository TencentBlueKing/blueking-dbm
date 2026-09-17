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

	"golang.org/x/text/encoding/simplifiedchinese"

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
	// encodingGBK 严格双向校验通过的 GBK/ANSI(936) 文件。
	// 该类文件仅在目标执行环境统一使用 sqlcmd -f 936 且数据库 collation 为 Chinese_PRC_* 时才安全，
	// 已由 dbactuator 侧的执行链路保证前置条件。
	encodingGBK     = "gbk"
	encodingUnknown = "unknown"
)

const (
	nonASCIIUTF8Message           = "文件编码校验失败：当前文件为无 BOM 的 UTF-8，且包含非 ASCII 字符。该格式在 Windows/sqlcmd 跨语言环境下可能被错误解析。请将文件转换为 UTF-8 with BOM 后重新提交。仅纯 ASCII 文件允许不带 BOM。若脚本中包含非 ASCII 字符串字面量，建议优先使用 N'...' 表示 Unicode 文本。"
	nonUTF8Message                = "文件编码校验失败：当前文件既不是 UTF-8，也不是合法的 GBK/ANSI(936)（例如可能是 Big5、Shift-JIS、EUC-KR 等其它本地编码，或文件已损坏）。请将文件转换为 UTF-8 with BOM 后重新提交。仅纯 ASCII 文件允许不带 BOM。"
	unsupportedEncodingMessageFmt = "文件编码校验失败：检测到不支持的编码 %s。请将文件转换为 UTF-8 with BOM 后重新提交。仅纯 ASCII 文件允许不带 BOM。"
	// gbkDowngradeMessage GBK/ANSI(936) 通道的软提示（Pass 状态下附带），
	// 用于让用户提前意识到该通道的字符集天花板，需要更完整字符集时应主动切换到 UTF-8 with BOM。
	gbkDowngradeMessage = "文件识别为 GBK/ANSI(936)，已按兼容通道放行执行。" +
		"注意：GBK 字符集不支持 emoji（如 👍 😀）、CJK 扩展字（如 𠮷、biáng 字 𰻞）、" +
		"少数民族文字（藏文、蒙文、维吾尔文等）及其它 Unicode 补充平面字符。" +
		"如脚本涉及此类字符，请改用 UTF-8 with BOM 编码以获得完整的 Unicode 支持。"
)

// EncodingChecker 文件编码检查器。
// 允许以下几类文件通过：
//   - UTF-8 with BOM
//   - 无 BOM 但全文仅包含 ASCII 字节的文件
//   - 严格 GBK/ANSI(936) 文件（需目标执行链路配合 sqlcmd -f 936）
//
// 其余无 BOM 且包含非 ASCII 的 UTF-8 文件、以及非 UTF-8 且非 GBK 的文件一律拒绝。
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
	case encodingGBK:
		// GBK 放行前提：目标执行环境统一使用 sqlcmd -f 936，且数据库 collation 为 Chinese_PRC_* 系列。
		// 该前提由 dbactuator 侧的执行链路（sqlfiles_execute.go）保证。
		// 状态判 Pass，但附带一条"降级提示"，让上层/前端可展示给用户，
		// 使其意识到 GBK 通道的字符集边界（不支持 emoji、CJK 扩展字、少数民族文字等）。
		result.Status = sqlserver.FileCheckPass
		result.Message = gbkDowngradeMessage
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
//
// 判定顺序（重要，影响正确性）：
//  1. 各类 BOM 优先
//  2. 纯 ASCII 放行
//  3. 合法 UTF-8（无 BOM 含非 ASCII）—— 拒绝，避免跨环境风险
//  4. 严格 GBK（decode + 反向 encode 字节一致）—— 放行
//  5. 其它 —— unknown（拒绝，包括 Big5 / Shift-JIS / EUC-KR / 已损坏文件等）
//
// 之所以 GBK 判定要放在 utf8.Valid 之后，是因为 GBK 汉字字节序列几乎不可能构成合法 UTF-8，
// 而"无 BOM UTF-8 含中文"必须优先按 nonASCIIUTF8Message 拒绝，避免被误判为 GBK。
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
	case isStrictGBK(content):
		return encodingGBK
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

// isStrictGBK 严格判定字节序列是否为合法 GBK/ANSI(936)：
//  1. 能被 GBK 解码器无错解码
//  2. 解码得到的 Unicode 文本再用 GBK 编码器编回，字节必须与原文完全一致
//
// 双向一致校验的意义：单纯"能 decode 成功"不足以证明文件真是 GBK——
// 因为 Big5 / Shift-JIS / EUC-KR 等其它 ANSI 编码的字节空间与 GBK 高度重叠，
// 它们的字节序列也可能被 GBK 解码器"识别"，但解出来的字符与原意完全不同。
// 反向 encode 回到原字节，可以排除绝大多数这类伪装。
func isStrictGBK(content []byte) bool {
	if len(content) == 0 {
		return false
	}
	dec := simplifiedchinese.GBK.NewDecoder()
	decoded, err := dec.Bytes(content)
	if err != nil {
		return false
	}
	enc := simplifiedchinese.GBK.NewEncoder()
	reencoded, err := enc.Bytes(decoded)
	if err != nil {
		return false
	}
	return bytes.Equal(content, reencoded)
}
