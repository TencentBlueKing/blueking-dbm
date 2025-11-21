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
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/model"
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
	AlterTableRule        AlterTableRule        `yaml:"AlterTableRule"`
	DmlRule               DmlRule               `yaml:"DmlRule"`
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
		// 尝试多个可能的路径
		possiblePaths := []string{
			DefaultSpiderRuleFile,               // 当前目录
			"../../" + DefaultSpiderRuleFile,    // 从app/syntax向上两级
			"../../../" + DefaultSpiderRuleFile, // 从更深的目录
		}

		for _, path := range possiblePaths {
			if cmutil.FileExists(path) {
				fileContent, err = os.ReadFile(path)
				if err == nil {
					break
				}
			}
		}

		// 如果仍然找不到且在测试环境，使用最小配置
		if err != nil && len(fileContent) == 0 {
			if testEnv := os.Getenv("TESTING"); testEnv == "true" {
				logger.Warn("Spider rule file not found, using minimal configuration for testing")
				// 创建一个最小的规则配置用于测试
				SR = &SpiderRules{
					CommandRule: CommandRule{
						HighRiskCommandRule: &RuleItem{
							Expr: " Val in Item ",
							Desc: "高危命令",
							Item: []string{},
						},
						BanCommandRule: &RuleItem{
							Expr: " Val in Item ",
							Desc: "禁用命令",
							Ban:  true,
							Item: []string{},
						},
					},
				}
				return
			}
		}
	}
	if err != nil {
		logger.Fatal("read rule config file failed %s", err.Error())
		return
	}
	if err = yaml.Unmarshal(fileContent, SR); err != nil {
		logger.Fatal("yaml Unmarshal failed %s", err.Error())
		return
	}
	// 在测试环境或DB未初始化时跳过数据库加载
	// 检查 DB 是否为 nil，避免在测试环境中访问未初始化的数据库
	if os.Getenv("TESTING") != "true" && model.DB != nil {
		if err = traverseLoadRule(app.Spider, *SR); err != nil {
			logger.Error("load rule from database failed %s", err.Error())
		}
	}
	var initCompiles = []*RuleItem{}
	initCompiles = append(initCompiles, traverseRule(SR.CommandRule)...)
	initCompiles = append(initCompiles, traverseRule(SR.SpiderCreateTableRule)...)
	initCompiles = append(initCompiles, traverseRule(SR.AlterTableRule)...)
	initCompiles = append(initCompiles, traverseRule(SR.DmlRule)...)
	for _, c := range initCompiles {
		if err = c.compile(); err != nil {
			logger.Fatal("compile rule failed %s", err.Error())
			return
		}
	}
}

// ReloadRuleFromDb reload rule from db
func ReloadRuleFromDb() (err error) {
	logger.Info("reload mysql rule from db")
	if err = traverseLoadRule(app.Spider, *R); err != nil {
		logger.Error("load rule from database failed %s", err.Error())
		return err
	}
	var initCompiles = []*RuleItem{}
	initCompiles = append(initCompiles, traverseRule(R.CommandRule)...)
	initCompiles = append(initCompiles, traverseRule(R.CreateTableRule)...)
	initCompiles = append(initCompiles, traverseRule(R.AlterTableRule)...)
	initCompiles = append(initCompiles, traverseRule(R.DmlRule)...)
	for _, c := range initCompiles {
		if err = c.compile(); err != nil {
			logger.Error("compile rule failed %s", err.Error())
			return err
		}
	}
	logger.Info("reload spider rule from db success")
	if err = traverseLoadRule(app.Spider, *SR); err != nil {
		logger.Error("load rule from database failed %s", err.Error())
		return err
	}
	initCompiles = []*RuleItem{}
	initCompiles = append(initCompiles, traverseRule(SR.CommandRule)...)
	initCompiles = append(initCompiles, traverseRule(SR.SpiderCreateTableRule)...)
	for _, c := range initCompiles {
		if err = c.compile(); err != nil {
			logger.Error("compile rule failed %s", err.Error())
			return err
		}
	}
	return nil
}
