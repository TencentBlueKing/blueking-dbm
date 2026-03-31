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

package middleware

import (
	"k8s-dbs/i18n"
	i18nctx "k8s-dbs/i18n/context"

	"github.com/gin-gonic/gin"
)

// I18nMiddleware 创建 i18n 中间件，检测客户端语言偏好并设置 localizer
func I18nMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		lang := detectLanguage(c)
		localizer := i18n.NewLocalizer(lang)

		c.Set(i18nctx.LanguageKey, localizer)

		c.Next()
	}
}

// detectLanguage 从请求中检测首选语言
func detectLanguage(c *gin.Context) string {
	const langKey = "blueking_language"

	// 从 Cookie 获取
	if cookie, err := c.Cookie(langKey); err == nil && cookie != "" {
		if isSupported(cookie) {
			return cookie
		}
	}

	// 从 Header 获取
	if headerLang := c.GetHeader(langKey); headerLang != "" {
		if isSupported(headerLang) {
			return headerLang
		}
	}

	// 从 Accept-Language 请求头获取
	if acceptLang := c.GetHeader("Accept-Language"); acceptLang != "" {
		lang := parseAcceptLanguage(acceptLang)
		if isSupported(lang) {
			return lang
		}
	}

	// 默认语言
	return i18n.DefaultLanguage
}

// parseAcceptLanguage 从 Accept-Language 头提取主要语言
func parseAcceptLanguage(header string) string {
	if header == "" {
		return ""
	}

	// 简单解析: 提取第一个语言标签
	for i, c := range header {
		if c == ',' || c == ';' {
			return header[:i]
		}
	}
	return header
}

// isSupported 检查给定语言是否支持
func isSupported(lang string) bool {
	for _, supported := range i18n.SupportedLanguages {
		if lang == supported {
			return true
		}
	}
	return false
}
