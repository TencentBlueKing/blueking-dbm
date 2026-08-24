// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/samber/lo"
	"gopkg.in/yaml.v2"

	"dbm-services/common/db-event-consumer/pkg/base"
	"dbm-services/common/db-event-consumer/pkg/cst"
	"dbm-services/common/db-event-consumer/pkg/model"
	"dbm-services/common/db-event-consumer/pkg/sinker"
)

var MainConfig *mainConfig
var SinkerConfigs []*SinkerConfig

func init() {
	MainConfig = &mainConfig{}
	SinkerConfigs = make([]*SinkerConfig, 0)
	_ = sinker.RegisterModelSinker(&model.MysqlBackupResultModel{})
	_ = sinker.RegisterModelSinker(&model.BinlogFileModel{})
	_ = sinker.RegisterModelSinker(&model.MysqlBackupStatusModel{})
	_ = sinker.RegisterModelSinker(&model.MysqlPartitionResultModel{})
	_ = sinker.RegisterModelSinker(&model.MysqlTableSize{})
	_ = sinker.RegisterModelSinker(&model.MysqlSlowLogModel{})
	_ = sinker.RegisterModelSinker(&model.MysqlProxyConnlog{})
	_ = sinker.RegisterModelSinker(&model.DbmRetryEvent{})

	_ = sinker.RegisterModelSinker(&model.RedisBackupResultModel{})
	_ = sinker.RegisterModelSinker(&model.RedisBinlogFileModel{})
	_ = sinker.RegisterModelSinker(&model.RedisBackupStatusModel{})

	_ = sinker.RegisterModelWriteType(&sinker.MysqlWriter{})
	_ = sinker.RegisterModelWriteType(&sinker.XormWriter{})
	_ = sinker.RegisterModelWriteType(&sinker.MysqlRawWriter{})
	_ = sinker.RegisterModelWriteType(&sinker.DorisWriter{})
	_ = sinker.RegisterModelWriteType(&sinker.DorisHttpWriter{})
}

type mainConfig struct {
	Log        *LogConfig           `yaml:"log"`
	KafkaInfo  *KafkaMeta           `yaml:"kafka_info"`
	BkmApiInfo *BkmApiInfo          `yaml:"bkm_api_info"`
	BkmReport  *base.BKReportConfig `yaml:"bkm_report"`
	OtelPort   int                  `yaml:"otel_port"`
}

func InitConfig(configPath string) {
	mainConfigFile := InitMainConfig(configPath)
	var err error
	SinkerConfigs, err = InitSinkerConfig(mainConfigFile)
	if err != nil {
		panic(err)
	}
}

func InitMainConfig(configPath string) (configFile string) {
	if !filepath.IsAbs(configPath) {
		cwd, err := os.Getwd()
		if err != nil {
			panic(err)
		}
		configPath = filepath.Join(cwd, configPath)
	}

	content, err := os.ReadFile(configPath)
	if err != nil {
		panic(err)
	}

	err = yaml.Unmarshal(content, MainConfig)
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
	var checkDup = make(map[string]struct{})
	for _, f := range files {
		//s := SinkerConfig{}
		var sinkers []*SinkerConfig
		content, err := os.ReadFile(f)
		if err != nil {
			panic(err)
		}
		if err = yaml.Unmarshal(content, &sinkers); err != nil {
			os.Stderr.WriteString(fmt.Sprintf("error parsing %s: %v", f, err))
			continue
		}

		allSinkers = append(allSinkers, sinkers...)
		for _, s := range sinkers {
			if s.StrictSchema == nil {
				s.StrictSchema = &cst.PtrTrue
			}
			// 使用 topic/bk_collector_name/bk_data_id/group_id_suffix 组合生成唯一名称
			name := fmt.Sprintf("%s-%s-%d-%s", s.Topic, s.BkCollectorName, s.BkDataId, s.GroupIdSuffix)
			if _, ok := checkDup[name]; ok {
				return nil, fmt.Errorf("duplicate sinker name %s", name)
			}
			checkDup[name] = struct{}{}

			if s.WriteMode == "" {
				s.WriteMode = cst.ModeReplace
			}
			if !lo.Contains([]string{cst.ModeInsertIgnore, cst.ModeInsert, cst.ModeUpsert, cst.ModeReplace}, s.WriteMode) {
				return nil, fmt.Errorf("invalid write_mode: %s", s.WriteMode)
			}
			if s.Topic == "" && s.BkDataId == 0 && s.BkCollectorName == "" {
				return nil, fmt.Errorf("topic or bk_data_id or bk_collector_name must be set")
			}
		}
	}
	return allSinkers, nil
}
