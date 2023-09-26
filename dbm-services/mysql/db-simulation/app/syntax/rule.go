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
	"fmt"
	"log"
	"os"
	"reflect"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/model"

	"github.com/antonmedv/expr"
	"github.com/antonmedv/expr/vm"
	"gopkg.in/yaml.v2"
	"gorm.io/gorm"
)

// R TODO
var R *Rules

// Checker TODO
type Checker interface {
	Checker(mysqlVersion string) *CheckerResult
}

// CheckerResult TODO
type CheckerResult struct {
	BanWarns  []string
	RiskWarns []string
}

// IsPass TODO
func (c CheckerResult) IsPass() bool {
	return len(c.BanWarns) == 0 && len(c.RiskWarns) == 0
}

// Parse TODO
func (c *CheckerResult) Parse(rule *RuleItem, val interface{}, s string) {
	matched, err := rule.CheckItem(val)
	if matched {
		if rule.Ban {
			c.BanWarns = append(c.BanWarns, fmt.Sprintf("%s\n%s", err.Error(), s))
		} else {
			c.RiskWarns = append(c.RiskWarns, fmt.Sprintf("%s\n%s", err.Error(), s))
		}
	}
}

// ParseBultinBan TODO
func (c *CheckerResult) ParseBultinBan(f func() (bool, string)) {
	matched, msg := f()
	if matched {
		c.BanWarns = append(c.BanWarns, msg)
	}
}

const (
	// DEFAUTL_RULE_FILE TODO
	DEFAUTL_RULE_FILE = "rule.yaml"
	// DEFAUTL_SPIDER_RULE_FILE TODO
	DEFAUTL_SPIDER_RULE_FILE = "spider_rule.yaml"
)

func init() {
	R = &Rules{}
	var fileContent []byte
	var err error
	if cmutil.FileExists(config.GAppConfig.RulePath) {
		fileContent, err = os.ReadFile(config.GAppConfig.RulePath)
	} else {
		fileContent, err = os.ReadFile(DEFAUTL_RULE_FILE)
	}
	if err != nil {
		logger.Error("failed to read the rule file:%s", err.Error())
		panic(err)
	}
	if err := yaml.Unmarshal(fileContent, R); err != nil {
		panic(err)
	}
	if err = traverseLoadRule(*R); err != nil {
		logger.Error("load rule from database failed %s", err.Error())
	}
	var initCompiles = []*RuleItem{}
	initCompiles = append(initCompiles, traverseRule(R.CommandRule)...)
	initCompiles = append(initCompiles, traverseRule(R.CreateTableRule)...)
	initCompiles = append(initCompiles, traverseRule(R.AlterTableRule)...)
	initCompiles = append(initCompiles, traverseRule(R.DmlRule)...)
	for _, c := range initCompiles {
		if err := c.Compile(); err != nil {
			panic(err)
		}
	}
}

// RuleItem TODO
type RuleItem struct {
	Item        interface{} `yaml:"item"`
	Val         interface{}
	ruleProgram *vm.Program
	Expr        string `yaml:"expr"`
	Desc        string `yaml:"desc"`
	Ban         bool   `yaml:"ban"`
}

// Rules TODO
type Rules struct {
	CommandRule     CommandRule     `yaml:"CommandRule"`
	CreateTableRule CreateTableRule `yaml:"CreateTableRule"`
	AlterTableRule  AlterTableRule  `yaml:"AlterTableRule"`
	DmlRule         DmlRule         `yaml:"DmlRule"`
	BuiltInRule     BuiltInRule     `yaml:"BuiltInRule"`
}

// BuiltInRule TODO
type BuiltInRule struct {
	TableNameSpecification TableNameSpecification `yaml:"TableNameSpecification"`
	ShemaNamespecification ShemaNamespecification `yaml:"ShemaNamespecification"`
}

// TableNameSpecification TODO
type TableNameSpecification struct {
	KeyWord     bool `yaml:"keyword"`
	SpeicalChar bool `yaml:"speicalChar"`
}

// ShemaNamespecification TODO
type ShemaNamespecification struct {
	KeyWord     bool `yaml:"keyword"`
	SpeicalChar bool `yaml:"speicalChar"`
	sysDbName   bool `yaml:"sysDbName"`
}

// CommandRule TODO
type CommandRule struct {
	HighRiskCommandRule *RuleItem `yaml:"HighRiskCommandRule"`
	BanCommandRule      *RuleItem `yaml:"BanCommandRule"`
}

// CreateTableRule TODO
type CreateTableRule struct {
	SuggestBlobColumCount *RuleItem `yaml:"SuggestBlobColumCount"`
	SuggestEngine         *RuleItem `yaml:"SuggestEngine"`
	NeedPrimaryKey        *RuleItem `yaml:"NeedPrimaryKey"`
	DefinerRule           *RuleItem `yaml:"DefinerRule"`
	NormalizedName        *RuleItem `yaml:"NormalizedName"`
}

// AlterTableRule TODO
type AlterTableRule struct {
	HighRiskType        *RuleItem `yaml:"HighRiskType"`
	HighRiskPkAlterType *RuleItem `yaml:"HighRiskPkAlterType"`
	AlterUseAfter       *RuleItem `yaml:"AlterUseAfter"`
	AddColumnMixed      *RuleItem `yaml:"AddColumnMixed"`
}

// DmlRule TODO
type DmlRule struct {
	DmlNotHasWhere *RuleItem `yaml:"DmlNotHasWhere"`
}

func traverseLoadRule(rulepointer interface{}) error {
	tv := reflect.TypeOf(rulepointer)
	v := reflect.ValueOf(rulepointer)
	var groupname, rulename string
	for i := 0; i < tv.NumField(); i++ {
		groupname = tv.Field(i).Name
		if v.Field(i).Type().Kind() == reflect.Struct {
			structField := v.Field(i).Type()
			for j := 0; j < structField.NumField(); j++ {
				rulename = structField.Field(j).Name
				drule, err := model.GetRuleByName(groupname, rulename)
				if err != nil {
					if err == gorm.ErrRecordNotFound {
						logger.Warn("not found group:%s,rule:%s rules in databases", groupname, rulename)
						continue
					}
					logger.Error("from db get  group:%s,rule:%s failed: %s", groupname, rulename, err.Error())
					return err
				}
				rule, err := parseRule(drule)
				if err != nil {
					logger.Error("parse rule failed %s", err.Error())
					return err
				}
				logger.Info("%v", &rule)
				v.Field(i).Field(j).Elem().Set(reflect.ValueOf(rule))
			}
		}
	}
	logger.Info("load AlterTableRule  %v", R.CommandRule.BanCommandRule.Item)
	return nil
}

func parseRule(drule model.TbSyntaxRule) (rule RuleItem, err error) {
	iv, err := model.GetItemVal(drule)
	if err != nil {
		return RuleItem{}, err
	}
	rule = RuleItem{
		Desc: drule.Desc,
		Ban:  drule.WarnLevel == 1,
		Expr: drule.Expr,
		Item: iv,
	}
	return
}

// traverseRule 遍历规则
func traverseRule(v interface{}) (rules []*RuleItem) {
	value := reflect.ValueOf(v) // coordinate 是一个 Coordinate 实例
	for num := 0; num < value.NumField(); num++ {
		rule := value.Field(num).Interface().(*RuleItem)
		rules = append(rules, rule)
	}
	return rules
}

// Env TODO
type Env struct {
	Val  interface{}
	Item interface{}
}

// Compile TODO
func (i *RuleItem) Compile() (err error) {
	p, err := expr.Compile(i.Expr, expr.Env(Env{}), expr.AsBool())
	if err != nil {
		log.Printf("expr.Compile error %s\n", err.Error())
		return err
	}
	i.ruleProgram = p
	return
}

// CheckItem 运行规则检查
//
//	@receiver i
func (i *RuleItem) CheckItem(val interface{}) (matched bool, err error) {
	// i.ruleProgram是具体执行的规则，此处为接下来如何对比  对比item与val
	// Item: i.Item是rule.yaml中的规定项
	// Val:  val是Tparsemysql分析后的结果，存储在json文件中，读取后获得相应值
	p, err := expr.Run(i.ruleProgram, Env{
		Item: i.Item,
		Val:  val,
	})
	if err != nil {
		return false, err
	}
	if v, assetok := p.(bool); assetok {
		matched = v
	}
	if !matched {
		return false, fmt.Errorf("")
	}
	return matched, fmt.Errorf("%s:%v", i.Desc, val)
}
