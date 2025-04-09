// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

import (
	"os"
	"path/filepath"

	"github.com/spf13/viper"
	"gopkg.in/yaml.v2"
)

var MainConfig *mainConfig
var SinkerConfigs []*SinkerConfig

func init() {
	MainConfig = &mainConfig{}
	SinkerConfigs = make([]*SinkerConfig, 0)
}

func InitConfig() {
	mainConfigFile := InitMainConfig()
	var err error
	SinkerConfigs, err = InitSinkerConfig(mainConfigFile)
	if err != nil {
		panic(err)
	}
}

func InitMainConfig() (configFile string) {
	configPath := viper.GetString("config")
	if !filepath.IsAbs(configPath) {
		cwd, err := os.Getwd()
		if err != nil {
			panic(err)
		}

		configPath = filepath.Join(cwd, configPath)
		viper.Set("config", configPath)
	}

	content, err := os.ReadFile(configPath)
	if err != nil {
		panic(err)
	}

	err = yaml.UnmarshalStrict(content, MainConfig)
	if err != nil {
		panic(err)
	}
	return configPath
}

func InitSinkerConfig(mainConfFile string) ([]*SinkerConfig, error) {
	// search server.<port>.yaml
	serverConfigName := "data.*.yaml"
	serverConfigPath := filepath.Join(filepath.Dir(mainConfFile), serverConfigName)
	files, err := filepath.Glob(serverConfigPath)
	if err != nil {
		return nil, err
	}
	var allSinkers []*SinkerConfig
	for _, f := range files {
		//s := SinkerConfig{}
		var sinkers []*SinkerConfig
		content, err := os.ReadFile(f)
		if err != nil {
			panic(err)
		}
		if err = yaml.UnmarshalStrict(content, &sinkers); err != nil {
			continue
		}
		allSinkers = append(allSinkers, sinkers...)
	}
	return allSinkers, nil
}
