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
	"strings"
	"unicode"

	"golang.org/x/text/cases"
	"golang.org/x/text/language"
)

// ToUpper 将字符串转换为大写
func ToUpper(s string) string {
	return strings.ToUpper(s)
}

// ToLower 将字符串转换为小写
func ToLower(s string) string {
	return strings.ToLower(s)
}

// Trim 去除字符串首尾的空白字符
func Trim(s string) string {
	return strings.TrimSpace(s)
}

// TrimSpace 去除字符串中的所有空白字符（包括内部）
func TrimSpace(s string) string {
	return strings.Join(strings.Fields(s), "")
}

// TrimPrefix 去除字符串的前缀
func TrimPrefix(s, prefix string) string {
	return strings.TrimPrefix(s, prefix)
}

// TrimSuffix 去除字符串的后缀
func TrimSuffix(s, suffix string) string {
	return strings.TrimSuffix(s, suffix)
}

// Contains 检查字符串是否包含子串
func Contains(s, substr string) bool {
	return strings.Contains(s, substr)
}

// ContainsAny 检查字符串是否包含字符集合中的任意一个字符
func ContainsAny(s string, chars string) bool {
	return strings.ContainsAny(s, chars)
}

// HasPrefix 检查字符串是否有指定的前缀
func HasPrefix(s, prefix string) bool {
	return strings.HasPrefix(s, prefix)
}

// HasSuffix 检查字符串是否有指定的后缀
func HasSuffix(s, suffix string) bool {
	return strings.HasSuffix(s, suffix)
}

// Index 返回子串在字符串中的索引位置，如果未找到则返回 -1
func Index(s, substr string) int {
	return strings.Index(s, substr)
}

// LastIndex 返回子串在字符串中最后一次出现的索引位置，如果未找到则返回 -1
func LastIndex(s, substr string) int {
	return strings.LastIndex(s, substr)
}

// Replace 替换字符串中的子串
func Replace(s, old, replace string, n int) string {
	return strings.Replace(s, old, replace, n)
}

// ReplaceAll 替换字符串中的所有匹配子串
func ReplaceAll(s, old, replace string) string {
	return strings.ReplaceAll(s, old, replace)
}

// Split 按照指定的分隔符分割字符串
func Split(s, sep string) []string {
	return strings.Split(s, sep)
}

// SplitN 按照指定的分隔符分割字符串，最多分割 n 次
func SplitN(s, sep string, n int) []string {
	return strings.SplitN(s, sep, n)
}

// Join 将字符串切片连接成一个字符串，使用指定的分隔符
func Join(elems []string, sep string) string {
	return strings.Join(elems, sep)
}

// Repeat 重复字符串指定次数
func Repeat(s string, count int) string {
	return strings.Repeat(s, count)
}

// ToTitle 将字符串中的每个单词的首字母大写
func ToTitle(s string) string {
	caser := cases.Title(language.English)
	return caser.String(s)
}

// ToCamelCase 将 snake_case 或 kebab-case 转换为 CamelCase
func ToCamelCase(s string) string {
	words := splitWords(s)
	for i, word := range words {
		if len(word) == 0 {
			continue
		}
		words[i] = string(unicode.ToUpper(rune(word[0]))) + word[1:]
	}
	return strings.Join(words, "")
}

// ToSnakeCase 将 CamelCase 转换为 snake_case
func ToSnakeCase(s string) string {
	var snake []rune
	for i, r := range s {
		if unicode.IsUpper(r) {
			if i > 0 {
				snake = append(snake, '_')
			}
			snake = append(snake, unicode.ToLower(r))
		} else {
			snake = append(snake, r)
		}
	}
	return string(snake)
}

// ToKebabCase 将 CamelCase 转换为 kebab-case
func ToKebabCase(s string) string {
	var kebab []rune
	for i, r := range s {
		if unicode.IsUpper(r) {
			if i > 0 {
				kebab = append(kebab, '-')
			}
			kebab = append(kebab, unicode.ToLower(r))
		} else {
			kebab = append(kebab, r)
		}
	}
	return string(kebab)
}

// IsEmpty 检查字符串是否为空或仅包含空白字符
func IsEmpty(s string) bool {
	return len(strings.TrimSpace(s)) == 0
}

// Reverse 反转字符串
func Reverse(s string) string {
	runes := []rune(s)
	for i, j := 0, len(runes)-1; i < j; i, j = i+1, j-1 {
		runes[i], runes[j] = runes[j], runes[i]
	}
	return string(runes)
}

// RemoveChars 去除字符串中的指定字符
func RemoveChars(s string, chars string) string {
	var result strings.Builder
	for _, r := range s {
		if !strings.ContainsRune(chars, r) {
			result.WriteRune(r)
		}
	}
	return result.String()
}

// splitWords 将字符串分割为单词（支持 snake_case 和 kebab-case）
func splitWords(s string) []string {
	var words []string
	var current strings.Builder
	inWord := false

	for _, r := range s {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' {
			current.WriteRune(r)
			inWord = true
		} else if inWord {
			words = append(words, current.String())
			current.Reset()
			inWord = false

		}
	}
	if inWord {
		words = append(words, current.String())
	}

	// 处理连续的分隔符
	var cleaned []string
	for _, word := range words {
		if word != "" {
			cleaned = append(cleaned, word)
		}
	}

	return cleaned
}
