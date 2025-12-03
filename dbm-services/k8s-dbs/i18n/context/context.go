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

// Package context 提供在 gin.Context 中存储和获取语言翻译器的功能。
package context

import (
	"k8s-dbs/i18n"

	"github.com/gin-gonic/gin"
	goi18n "github.com/nicksnyder/go-i18n/v2/i18n"
)

// LanguageKey 在 gin.Context 中存储语言翻译器的 key
const LanguageKey = "i18n_language"

// GetLanguage 从 gin.Context 获取语言翻译器
func GetLanguage(c *gin.Context) *goi18n.Localizer {
	if localizer, exists := c.Get(LanguageKey); exists {
		if l, ok := localizer.(*goi18n.Localizer); ok {
			return l
		}
	}
	return i18n.NewLocalizer(i18n.DefaultLanguage)
}
