/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package syntax

import (
	"os"

	"gopkg.in/yaml.v2"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
)

// SR tendbcluster syntax rules
var SR *SpiderRules

// SpiderChecker tendbcluster syntax checker
type SpiderChecker interface {
	SpiderChecker(mysqlVersion string) *CheckerResult
}

// SpiderRules spdier 语法检查规则
type SpiderRules struct {
	CommandRule           CommandRule           `yaml:"CommandRule"`
	SpiderCreateTableRule SpiderCreateTableRule `yaml:"SpiderCreateTableRule"`
}

// SpiderCreateTableRule spider create table 建表规则
type SpiderCreateTableRule struct {
	ColChasetNotEqTbChaset                 *BoolRuleItem `yaml:"ColChasetNotEqTbChaset"`
	CreateWithSelect                       *BoolRuleItem `yaml:"CreateWithSelect"`
	ShardKeyNotPk                          *BoolRuleItem `yaml:"ShardKeyNotPk"`
	ShardKeyNotIndex                       *BoolRuleItem `yaml:"ShardKeyNotIndex"`
	IllegalComment                         *BoolRuleItem `yaml:"IllegalComment"`
	NoIndexExists                          *BoolRuleItem `yaml:"NoIndexExists"`
	NoPubColAtMultUniqueIndex              *BoolRuleItem `yaml:"NoPubColAtMultUniqueIndex"`
	MustSpecialShardKeyOnlyHaveCommonIndex *BoolRuleItem `yaml:"MustSpecialShardKeyOnlyHaveCommonIndex"`
	ShardKeyNotNull                        *BoolRuleItem `yaml:"ShardKeyNotNull"`
}

func init() {
	SR = &SpiderRules{}
	var fileContent []byte
	var err error
	if cmutil.FileExists(config.GAppConfig.SpiderRulePath) {
		fileContent, err = os.ReadFile(config.GAppConfig.SpiderRulePath)
	} else {
		fileContent, err = os.ReadFile(DefaultSpiderRuleFile)
	}
	if err != nil {
		logger.Fatal("read rule config file failed %s", err.Error())
		return
	}
	if err = yaml.Unmarshal(fileContent, SR); err != nil {
		logger.Fatal("yaml Unmarshal failed %s", err.Error())
		return
	}
	if config.GAppConfig.LoadRuleFromdb {
		if err = traverseLoadRule(*SR); err != nil {
			logger.Error("load rule from database failed %s", err.Error())
		}
	}
	var initCompiles = []*RuleItem{}
	initCompiles = append(initCompiles, traverseRule(SR.CommandRule)...)
	initCompiles = append(initCompiles, traverseRule(SR.SpiderCreateTableRule)...)
	for _, c := range initCompiles {
		if err = c.compile(); err != nil {
			logger.Fatal("compile rule failed %s", err.Error())
			return
		}
	}
}
