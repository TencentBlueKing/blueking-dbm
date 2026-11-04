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
	"encoding/json"
	"sync"

	"dbm-services/common/go-pubpkg/logger"
)

// commonRules 是 MySQL 与 Spider 命令规则的只读交集。
// ban 命中只记禁用。同一命令不再记高危。
type commonRules struct {
	ban      map[string]struct{}
	highRisk map[string]struct{}
}

var (
	commonOnce sync.Once
	commonRule commonRules
)

// CommonBanCommands 返回公共禁用命令集合的副本。
func CommonBanCommands() map[string]struct{} {
	return cloneCommandSet(loadCommonRules().ban)
}

// CommonHighRiskCommands 返回公共高危命令集合的副本。高危集合已去掉禁用命令。
func CommonHighRiskCommands() map[string]struct{} {
	return cloneCommandSet(loadCommonRules().highRisk)
}

func loadCommonRules() commonRules {
	commonOnce.Do(func() {
		ban := intersectCommands(commandNames(R.CommandRule.BanCommandRule), commandNames(SR.CommandRule.BanCommandRule))
		highRisk := intersectCommands(
			commandNames(R.CommandRule.HighRiskCommandRule),
			commandNames(SR.CommandRule.HighRiskCommandRule),
		)
		for cmd := range ban {
			delete(highRisk, cmd)
		}
		commonRule = commonRules{ban: ban, highRisk: highRisk}
	})
	return commonRule
}

func commandNames(rule *RuleItem) map[string]struct{} {
	names := map[string]struct{}{}
	if rule == nil || rule.Item == nil {
		return names
	}
	switch items := rule.Item.(type) {
	case []string:
		for _, name := range items {
			names[name] = struct{}{}
		}
	case []interface{}:
		for _, item := range items {
			name, ok := item.(string)
			if !ok {
				continue
			}
			names[name] = struct{}{}
		}
	}
	return names
}

func intersectCommands(left, right map[string]struct{}) map[string]struct{} {
	out := make(map[string]struct{})
	for name := range left {
		if _, ok := right[name]; ok {
			out[name] = struct{}{}
		}
	}
	return out
}

func cloneCommandSet(in map[string]struct{}) map[string]struct{} {
	out := make(map[string]struct{}, len(in))
	for name := range in {
		out[name] = struct{}{}
	}
	return out
}

// ApplyCommon 对一条已解析语句套用公共规则，并把命中写进 BanWarnings / RiskWarnings。
func (c *CheckInfo) ApplyCommon(res ParseLineQueryBase, line []byte) error {
	result := &CheckerResult{}
	applyCommonCommand(result, res.Command, loadCommonRules())
	err := applyCommonStatement(result, res, line)
	c.copyCommonWarns(res, result)
	return err
}

func applyCommonCommand(r *CheckerResult, command string, rules commonRules) {
	if _, banned := rules.ban[command]; banned {
		parseSharedRule(r, R.CommandRule.BanCommandRule, command, "", "")
		return
	}
	if _, risky := rules.highRisk[command]; risky {
		parseSharedRule(r, R.CommandRule.HighRiskCommandRule, command, "", "")
	}
}

func applyCommonStatement(r *CheckerResult, res ParseLineQueryBase, line []byte) error {
	switch res.Command {
	case SQLTypeAlterTable:
		return applyCommonAlter(r, line)
	case SQLTypeUpdate:
		return applyCommonUpdate(r, line)
	case SQLTypeDelete:
		return applyCommonDelete(r, line)
	case SQLTypeCreateTable:
		return applyCommonCreateTable(r, line)
	case SQLTypeCreateDb:
		return applyCommonCreateDB(r, line)
	case SQLTypeCreateView, SQLTypeCreateProcedure, SQLTypeCreateFunction, SQLTypeCreateTrigger,
		SQLTypeCreateEvent, SQLTypeCreateSpFunction:
		return applyCommonDefiner(r, line)
	default:
		return nil
	}
}

func applyCommonAlter(r *CheckerResult, line []byte) error {
	var alter AlterTableResult
	if err := unmarshalCommonLine(line, &alter); err != nil {
		return err
	}
	r.ObjName = alter.TableName
	for _, cmd := range alter.AlterCommands {
		desc := cmd.RiskObjectDesc()
		parseSharedRule(r, R.AlterTableRule.HighRiskType, cmd.HighRiskTypeVal(), cmd.ExtraMessageKey(), desc)
		parseSharedRule(r, R.AlterTableRule.HighRiskPkAlterType, cmd.GetPkAlterType(), "", desc)
		parseSharedRule(r, R.AlterTableRule.AlterUseAfter, cmd.After, "", "")
		if R.BuiltInRule.TableNameSpecification.KeyWord && cmd.Type == AlterTypeAddColumn {
			colName := cmd.ColDef.ColName
			r.ParseBuiltinRisk(func() (bool, string) {
				return KeyWordValidator("", colName)
			})
		}
	}
	parseSharedRule(r, R.AlterTableRule.AddColumnMixed, alter.GetAllAlterType(), "", "")
	return nil
}

func applyCommonUpdate(r *CheckerResult, line []byte) error {
	var update UpdateResult
	if err := unmarshalCommonLine(line, &update); err != nil {
		return err
	}
	applyCommonDML(r, update.TableName, update.HasWhere, update.Limit)
	return nil
}

func applyCommonDelete(r *CheckerResult, line []byte) error {
	var del DeleteResult
	if err := unmarshalCommonLine(line, &del); err != nil {
		return err
	}
	applyCommonDML(r, del.TableName, del.HasWhere, del.Limit)
	return nil
}

func applyCommonDML(r *CheckerResult, table string, hasWhere bool, limit int) {
	r.ObjName = table
	parseSharedRule(r, R.DmlRule.DmlNotHasWhere, hasWhere || limit > 0, "", "")
}

func applyCommonCreateTable(r *CheckerResult, line []byte) error {
	var create CreateTableResult
	if err := unmarshalCommonLine(line, &create); err != nil {
		return err
	}
	r.ObjName = create.TableName
	if R.BuiltInRule.TableNameSpecification.KeyWord {
		tableName := create.TableName
		r.ParseBuiltinRisk(func() (bool, string) {
			return KeyWordValidator("", tableName)
		})
	}
	if R.BuiltInRule.TableNameSpecification.SpecialChar {
		tableName := create.TableName
		r.ParseBuiltinBan(func() (bool, string) {
			return SpecialCharValidator(tableName)
		})
	}
	return nil
}

func applyCommonCreateDB(r *CheckerResult, line []byte) error {
	var create CreateDBResult
	if err := unmarshalCommonLine(line, &create); err != nil {
		return err
	}
	r.ObjName = create.DbName
	r.IsDbName = true
	if R.BuiltInRule.SchemaNameSpecification.KeyWord {
		dbName := create.DbName
		r.ParseBuiltinRisk(func() (bool, string) {
			return KeyWordValidator("", dbName)
		})
	}
	if R.BuiltInRule.SchemaNameSpecification.SpecialChar {
		dbName := create.DbName
		r.ParseBuiltinBan(func() (bool, string) {
			return SpecialCharValidator(dbName)
		})
	}
	return nil
}

func applyCommonDefiner(r *CheckerResult, line []byte) error {
	var definer DefinerBase
	if err := unmarshalCommonLine(line, &definer); err != nil {
		return err
	}
	r.ObjName = definer.SpName
	parseSharedRule(r, R.CreateTableRule.DefinerRule, definer.Definer.User+"@"+definer.Definer.Host, "", "")
	return nil
}

func parseSharedRule(r *CheckerResult, rule *RuleItem, val interface{}, extraKey, additional string) {
	if rule == nil {
		return
	}
	r.ParseWithExtraKey(rule, val, extraKey, additional)
}

func unmarshalCommonLine(line []byte, dest interface{}) error {
	if err := json.Unmarshal(line, dest); err != nil {
		logger.Error("json unmarshal line failed %s", err.Error())
		return err
	}
	return nil
}

func (c *CheckInfo) copyCommonWarns(res ParseLineQueryBase, result *CheckerResult) {
	if result == nil {
		return
	}
	for _, warn := range result.BanWarns {
		c.BanWarnings = append(c.BanWarnings, RiskInfo{
			Line:        res.Line,
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    warn,
		})
	}
	for _, warn := range result.RiskWarns {
		c.RiskWarnings = append(c.RiskWarnings, RiskInfo{
			Line:        res.Line,
			Sqltext:     res.QueryString,
			CommandType: res.Command,
			WarnInfo:    warn,
		})
	}
}
