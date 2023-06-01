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
		logger.Error("read rule config file failed %s", err.Error())
		panic(err)
	}
	if err = yaml.Unmarshal(fileContent, SR); err != nil {
		logger.Error("yaml Unmarshal failed %s", err.Error())
		panic(err)
	}
	//	panic("panic there..")
	if err = traverseLoadRule(*SR); err != nil {
		logger.Error("load rule from database failed %s", err.Error())
	}
	var initCompiles = []*RuleItem{}
	initCompiles = append(initCompiles, traverseRule(SR.CommandRule)...)
	initCompiles = append(initCompiles, traverseRule(SR.SpiderCreateTableRule)...)
	for _, c := range initCompiles {
		if err = c.Compile(); err != nil {
			panic(err)
		}
	}
}

// SpiderRules TODO
type SpiderRules struct {
	CommandRule           CommandRule           `yaml:"CommandRule"`
	SpiderCreateTableRule SpiderCreateTableRule `yaml:"SpiderCreateTableRule"`
}

// SpiderCreateTableRule TODO
type SpiderCreateTableRule struct {
	ColChasetNotEqTbChaset *RuleItem `yaml:"ColChasetNotEqTbChaset"`
	CreateWithSelect       *RuleItem `yaml:"CreateWithSelect"`
	CreateTbLike           *RuleItem `yaml:"CreateTbLike"`
	ShardKeyNotPk          *RuleItem `yaml:"ShardKeyNotPk"`
	ShardKeyNotIndex       *RuleItem `yaml:"ShardKeyNotIndex"`
	IllegalComment         *RuleItem `yaml:"IllegalComment"`
}
