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

// Package i18n 提供国际化(i18n)支持，包括多语言消息的加载、翻译和管理功能。
package i18n

import (
	"embed"
	"sync"

	"github.com/nicksnyder/go-i18n/v2/i18n"
	"golang.org/x/text/language"
	"gopkg.in/yaml.v3"
)

//go:embed locales/*.yaml
var localeFS embed.FS

var (
	bundle *i18n.Bundle
	once   sync.Once
)

// DefaultLanguage 默认语言
const DefaultLanguage = "zh-CN"

// SupportedLanguages 支持的语言列表
var SupportedLanguages = []string{"en", "zh-CN"}

// Init 初始化 i18n bundle，加载所有语言文件
func Init() error {
	var initErr error
	once.Do(func() {
		bundle = i18n.NewBundle(language.Chinese)
		bundle.RegisterUnmarshalFunc("yaml", yaml.Unmarshal)

		localeFiles := []string{"en.yaml", "zh-CN.yaml"}
		for _, file := range localeFiles {
			_, err := bundle.LoadMessageFileFS(localeFS, "locales/"+file)
			if err != nil {
				initErr = err
				return
			}
		}
	})
	return initErr
}

// GetBundle 返回已初始化的 i18n bundle
func GetBundle() *i18n.Bundle {
	return bundle
}

// NewLocalizer 为指定语言创建 Localizer
func NewLocalizer(langs ...string) *i18n.Localizer {
	if bundle == nil {
		return nil
	}
	return i18n.NewLocalizer(bundle, langs...)
}

// Translate 根据消息 ID 翻译消息
func Translate(localizer *i18n.Localizer, msgID string) string {
	if localizer == nil {
		return msgID
	}
	msg, err := localizer.Localize(&i18n.LocalizeConfig{
		MessageID: msgID,
	})
	if err != nil {
		return msgID
	}
	return msg
}

// TranslateWithData 翻译带模板数据的消息
func TranslateWithData(localizer *i18n.Localizer, msgID string, data map[string]interface{}) string {
	if localizer == nil {
		return msgID
	}
	msg, err := localizer.Localize(&i18n.LocalizeConfig{
		MessageID:    msgID,
		TemplateData: data,
	})
	if err != nil {
		return msgID
	}
	return msg
}
