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
	"os"
	"reflect"
	"strings"

	"github.com/antonmedv/expr"
	"github.com/antonmedv/expr/vm"
	"gopkg.in/yaml.v2"
	"gorm.io/gorm"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/model"
)

// R TODO
var R *Rules

// Checker TODO
type Checker interface {
	Checker(mysqlVersion string) *CheckerResult
}

// CheckerResult 语法检查结果
type CheckerResult struct {
	ObjName   string
	IsSpFunc  bool
	IsSQLText bool
	BanWarns  []string
	RiskWarns []string
}

const (
	// DefaultRuleFile tendb 默认语法检查规则
	DefaultRuleFile = "rule.yaml"
	// DefaultSpiderRuleFile tendbcluster 默认语法检查规则
	DefaultSpiderRuleFile = "spider_rule.yaml"
)

func init() {
	R = &Rules{}
	var fileContent []byte
	var err error
	if cmutil.FileExists(config.GAppConfig.RulePath) {
		fileContent, err = os.ReadFile(config.GAppConfig.RulePath)
	} else {
		// 尝试多个可能的路径
		possiblePaths := []string{
			DefaultRuleFile,               // 当前目录
			"../../" + DefaultRuleFile,    // 从app/syntax向上两级
			"../../../" + DefaultRuleFile, // 从更深的目录
		}

		for _, path := range possiblePaths {
			if cmutil.FileExists(path) {
				fileContent, err = os.ReadFile(path)
				if err == nil {
					break
				}
			}
		}

		// 如果仍然找不到且在测试环境，使用相对于GOPATH的路径
		if err != nil && len(fileContent) == 0 {
			if testEnv := os.Getenv("TESTING"); testEnv == "true" {
				logger.Warn("Rule file not found, using minimal configuration for testing")
				// 创建一个最小的规则配置用于测试
				R = &Rules{
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
		logger.Fatal("failed to read the rule file:%s", err.Error())
		return
	}
	if err = yaml.Unmarshal(fileContent, R); err != nil {
		logger.Fatal("unmarshal rule config failed:%v", err)
	}
	// 是否从db中加载配置覆盖配置文件
	// 在测试环境或DB未初始化时跳过数据库加载
	// 检查 DB 是否为 nil，避免在测试环境中访问未初始化的数据库
	if config.GAppConfig.LoadRuleFromdb && os.Getenv("TESTING") != "true" && model.DB != nil {
		if err = traverseLoadRule(app.MySQL, *R); err != nil {
			logger.Error("load rule from database failed %s", err.Error())
		}
	}
	var initCompiles = []*RuleItem{}
	initCompiles = append(initCompiles, traverseRule(R.CommandRule)...)
	initCompiles = append(initCompiles, traverseRule(R.CreateTableRule)...)
	initCompiles = append(initCompiles, traverseRule(R.AlterTableRule)...)
	initCompiles = append(initCompiles, traverseRule(R.DmlRule)...)
	for _, c := range initCompiles {
		if err = c.compile(); err != nil {
			logger.Fatal("compile rule failed %s", err.Error())
			return
		}
	}
}

// IsPass syntax check ok
func (c CheckerResult) IsPass() bool {
	return len(c.BanWarns) == 0 && len(c.RiskWarns) == 0
}

// Parse do parse
func (c *CheckerResult) Parse(rule *RuleItem, val interface{}, additionalMsg string) {
	matched, err := rule.CheckItem(val)
	if matched {
		msg := strings.TrimSpace(fmt.Sprintf("%s %s\n%s\n%s", c.buildObjName(), err.Error(), additionalMsg, rule.Suggestion))
		if rule.Ban {
			c.BanWarns = append(c.BanWarns, msg)
		} else {
			c.RiskWarns = append(c.RiskWarns, msg)
		}
	}
}

// Trigger trigger
func (c *CheckerResult) Trigger(rule *BoolRuleItem, additionalMsg string) {
	// 表示检查开关关闭，跳过检查
	if !rule.TurnOn {
		return
	}
	msg := strings.TrimSpace(fmt.Sprintf("%s %s:%s\n%s", c.buildObjName(), rule.Desc, additionalMsg, rule.Suggestion))
	if rule.Ban {
		c.BanWarns = append(c.BanWarns, msg)
	} else {
		c.RiskWarns = append(c.RiskWarns, msg)
	}
}
func (c *CheckerResult) buildObjName() string {
	if c.IsSpFunc {
		return fmt.Sprintf("sp_name: %s ", c.ObjName)
	}
	if c.IsSQLText {
		return ""
	}
	if c.ObjName == "" {
		return ""
	}
	return fmt.Sprintf("table_name: %s ", c.ObjName)
}

// ParseBuiltinBan parse builtin ban
func (c *CheckerResult) ParseBuiltinBan(f func() (bool, string)) {
	matched, msg := f()
	if matched {
		c.BanWarns = append(c.BanWarns, fmt.Sprintf("%s  %s", c.buildObjName(), msg))
	}
}

// ParseBuiltinRisk parse builtin risk
func (c *CheckerResult) ParseBuiltinRisk(f func() (bool, string)) {
	matched, msg := f()
	if matched {
		c.RiskWarns = append(c.RiskWarns, fmt.Sprintf("%s %s", c.buildObjName(), msg))
	}
}

// RuleItem syntax rule item
type RuleItem struct {
	Item        interface{} `yaml:"item"`
	Val         interface{}
	ruleProgram *vm.Program
	Expr        string `yaml:"expr"`
	Desc        string `yaml:"desc"`
	Ban         bool   `yaml:"ban"`
	Suggestion  string `yaml:"suggestion"`
}

// BoolRuleItem 开关型规则，只需配置开启或者关闭即可
type BoolRuleItem struct {
	Desc       string `yaml:"desc"`
	Ban        bool   `yaml:"ban"`
	TurnOn     bool   `yaml:"turnOn"`
	Suggestion string `yaml:"suggestion"`
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
	TableNameSpecification  TableNameSpecification  `yaml:"TableNameSpecification"`
	SchemaNameSpecification SchemaNameSpecification `yaml:"SchemaNameSpecification"`
}

// TableNameSpecification table name check
type TableNameSpecification struct {
	KeyWord     bool `yaml:"keyword"`
	SpecialChar bool `yaml:"specialChar"`
}

// SchemaNameSpecification schema name check
type SchemaNameSpecification struct {
	KeyWord     bool `yaml:"keyword"`
	SpecialChar bool `yaml:"specialChar"`
}

// CommandRule TODO
type CommandRule struct {
	HighRiskCommandRule *RuleItem `yaml:"HighRiskCommandRule"`
	BanCommandRule      *RuleItem `yaml:"BanCommandRule"`
}

// CreateTableRule create table rules
type CreateTableRule struct {
	SuggestBlobColumCount *RuleItem `yaml:"SuggestBlobColumCount"`
	SuggestEngine         *RuleItem `yaml:"SuggestEngine"`
	NeedPrimaryKey        *RuleItem `yaml:"NeedPrimaryKey"`
	DefinerRule           *RuleItem `yaml:"DefinerRule"`
}

// AlterTableRule alter table rules
type AlterTableRule struct {
	HighRiskType        *RuleItem `yaml:"HighRiskType"`
	HighRiskPkAlterType *RuleItem `yaml:"HighRiskPkAlterType"`
	AlterUseAfter       *RuleItem `yaml:"AlterUseAfter"`
	AddColumnMixed      *RuleItem `yaml:"AddColumnMixed"`
}

// DmlRule dml rules
type DmlRule struct {
	DmlNotHasWhere *RuleItem `yaml:"DmlNotHasWhere"`
}

func traverseLoadRule(dbType string, rulePointer interface{}) error {
	tv := reflect.TypeOf(rulePointer)
	v := reflect.ValueOf(rulePointer)
	var groupName, ruleName string
	for i := 0; i < tv.NumField(); i++ {
		groupName = tv.Field(i).Name
		if v.Field(i).Type().Kind() == reflect.Struct {
			structField := v.Field(i).Type()
			for j := 0; j < structField.NumField(); j++ {
				ruleName = structField.Field(j).Name
				dRule, err := model.GetRuleByName(groupName, dbType, ruleName)
				if err != nil {
					if err == gorm.ErrRecordNotFound {
						logger.Warn("not found group:%s,rule:%s rules in databases", groupName, ruleName)
						continue
					}
					logger.Error("from db get  group:%s,rule:%s failed: %s", groupName, ruleName, err.Error())
					return err
				}
				rule, err := parseRule(dRule)
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

func parseRule(dRule model.TbSyntaxRule) (rule RuleItem, err error) {
	iv, err := model.GetItemVal(dRule)
	if err != nil {
		return RuleItem{}, err
	}
	rule = RuleItem{
		Desc: dRule.Desc,
		Ban:  dRule.WarnLevel == 1,
		Expr: dRule.Expr,
		Item: iv,
	}
	return
}

// traverseRule 遍历规则
func traverseRule(v interface{}) (rules []*RuleItem) {
	value := reflect.ValueOf(v) // coordinate 是一个 Coordinate 实例
	for num := 0; num < value.NumField(); num++ {
		rule, ok := value.Field(num).Interface().(*RuleItem)
		if ok {
			rules = append(rules, rule)
		}
	}
	return rules
}

// Env expr的运行环境
type Env struct {
	Val  interface{}
	Item interface{}
}

func (i *RuleItem) compile() (err error) {
	p, err := expr.Compile(i.Expr, expr.Env(Env{}), expr.AsBool())
	if err != nil {
		logger.Error("%s:expr.Compile error %s\n", i.Desc, err.Error())
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
	// Val:  val是TmysqlParse分析后的结果，存储在json文件中，读取后获得相应值
	p, err := expr.Run(i.ruleProgram, Env{
		Item: i.Item,
		Val:  val,
	})
	if err != nil {
		return false, err
	}
	if v, assetOk := p.(bool); assetOk {
		matched = v
	}
	if !matched {
		return false, fmt.Errorf("")
	}
	return matched, fmt.Errorf("%s,当前值:%v", i.Desc, val)
}
