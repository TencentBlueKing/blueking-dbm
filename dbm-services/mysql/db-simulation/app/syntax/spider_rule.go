package syntax

import (
	"os"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"

	"gopkg.in/yaml.v2"
)

// SR TODO
var SR *SpiderRules

// SpiderChecker TODO
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
	CreateTbLike                           *BoolRuleItem `yaml:"CreateTbLike"`
	ShardKeyNotPk                          *BoolRuleItem `yaml:"ShardKeyNotPk"`
	ShardKeyNotIndex                       *BoolRuleItem `yaml:"ShardKeyNotIndex"`
	IllegalComment                         *BoolRuleItem `yaml:"IllegalComment"`
	NoIndexExists                          *BoolRuleItem `yaml:"NoIndexExists"`
	NoPubColAtMultUniqueIndex              *BoolRuleItem `yaml:"NoPubColAtMultUniqueIndex"`
	MustSpecialShardKeyOnlyHaveCommonIndex *BoolRuleItem `yaml:"MustSpecialShardKeyOnlyHaveCommonIndex"`
}

func init() {
	SR = &SpiderRules{}
	var fileContent []byte
	var err error
	if cmutil.FileExists(config.GAppConfig.SpiderRulePath) {
		fileContent, err = os.ReadFile(config.GAppConfig.SpiderRulePath)
	} else {
		fileContent, err = os.ReadFile(DEFAUTL_SPIDER_RULE_FILE)
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
