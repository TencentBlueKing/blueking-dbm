/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package syntax_test

import (
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"dbm-services/mysql/db-simulation/app/syntax"
)

func TestCommonCommandSetsMatchRuleIntersection(t *testing.T) {
	ban := syntax.CommonBanCommands()
	highRisk := syntax.CommonHighRiskCommands()

	expectBan := intersectCommandNames(
		mustCommandNames(t, syntax.R.CommandRule.BanCommandRule),
		mustCommandNames(t, syntax.SR.CommandRule.BanCommandRule),
	)
	expectHigh := intersectCommandNames(
		mustCommandNames(t, syntax.R.CommandRule.HighRiskCommandRule),
		mustCommandNames(t, syntax.SR.CommandRule.HighRiskCommandRule),
	)
	for name := range expectBan {
		delete(expectHigh, name)
	}

	assert.Equal(t, expectBan, ban)
	assert.Equal(t, expectHigh, highRisk)
	_, banned := ban["alter_tablespace"]
	assert.True(t, banned)
	_, risky := highRisk["alter_tablespace"]
	assert.False(t, risky)
}

func TestAlterRuleItemsMatchBetweenMySQLAndSpider(t *testing.T) {
	pairs := []struct {
		name   string
		mysql  *syntax.RuleItem
		spider *syntax.RuleItem
	}{
		{"HighRiskType", syntax.R.AlterTableRule.HighRiskType, syntax.SR.AlterTableRule.HighRiskType},
		{"HighRiskPkAlterType", syntax.R.AlterTableRule.HighRiskPkAlterType, syntax.SR.AlterTableRule.HighRiskPkAlterType},
		{"AlterUseAfter", syntax.R.AlterTableRule.AlterUseAfter, syntax.SR.AlterTableRule.AlterUseAfter},
		{"AddColumnMixed", syntax.R.AlterTableRule.AddColumnMixed, syntax.SR.AlterTableRule.AddColumnMixed},
	}
	for _, pair := range pairs {
		require.NotNil(t, pair.mysql, pair.name)
		require.NotNil(t, pair.spider, pair.name)
		assert.Equal(t, ruleItemNames(t, pair.mysql.Item), ruleItemNames(t, pair.spider.Item), pair.name)
	}
}

func TestApplyCommonGrantUpdateAndSelect(t *testing.T) {
	grant := &syntax.CheckInfo{}
	err := grant.ApplyCommon(syntax.ParseLineQueryBase{
		Command:     "grant",
		QueryString: "GRANT ALL ON *.* TO 'a'@'%'",
		Line:        4,
	}, []byte(`{"command":"grant"}`))
	require.NoError(t, err)
	require.NotEmpty(t, grant.BanWarnings)
	assert.Empty(t, grant.RiskWarnings)
	assert.Equal(t, "grant", grant.BanWarnings[0].CommandType)
	assert.Equal(t, int64(4), grant.BanWarnings[0].Line)
	assert.Equal(t, "GRANT ALL ON *.* TO 'a'@'%'", grant.BanWarnings[0].Sqltext)
	assert.NotContains(t, grant.BanWarnings[0].WarnInfo, "[]:")

	updateLine, err := json.Marshal(syntax.UpdateResult{
		ParseBase: syntax.ParseBase{Command: syntax.SQLTypeUpdate, QueryString: "UPDATE t SET a=1"},
		TableName: "t",
		HasWhere:  false,
		Limit:     0,
	})
	require.NoError(t, err)
	update := &syntax.CheckInfo{}
	err = update.ApplyCommon(syntax.ParseLineQueryBase{
		Command:     syntax.SQLTypeUpdate,
		QueryString: "UPDATE t SET a=1",
		Line:        8,
	}, updateLine)
	require.NoError(t, err)
	assert.Empty(t, update.BanWarnings)
	require.NotEmpty(t, update.RiskWarnings)
	assert.Equal(t, syntax.SQLTypeUpdate, update.RiskWarnings[0].CommandType)
	assert.Equal(t, int64(8), update.RiskWarnings[0].Line)
	assert.Equal(t, "UPDATE t SET a=1", update.RiskWarnings[0].Sqltext)
	assert.NotContains(t, update.RiskWarnings[0].WarnInfo, "[]:")

	selected := &syntax.CheckInfo{}
	err = selected.ApplyCommon(syntax.ParseLineQueryBase{
		Command:     syntax.SQLTypeSelect,
		QueryString: "SELECT 1",
		Line:        1,
	}, []byte(`{"command":"select"}`))
	require.NoError(t, err)
	assert.Empty(t, selected.BanWarnings)
	assert.Empty(t, selected.RiskWarnings)
}

func mustCommandNames(t *testing.T, rule *syntax.RuleItem) map[string]struct{} {
	t.Helper()
	require.NotNil(t, rule)
	return commandNameSet(t, rule.Item)
}

func commandNameSet(t *testing.T, item interface{}) map[string]struct{} {
	t.Helper()
	names := map[string]struct{}{}
	switch items := item.(type) {
	case []string:
		for _, name := range items {
			names[name] = struct{}{}
		}
	case []interface{}:
		for _, raw := range items {
			name, ok := raw.(string)
			require.True(t, ok)
			names[name] = struct{}{}
		}
	default:
		t.Fatalf("command item type %T", item)
	}
	return names
}

func intersectCommandNames(left, right map[string]struct{}) map[string]struct{} {
	out := map[string]struct{}{}
	for name := range left {
		if _, ok := right[name]; ok {
			out[name] = struct{}{}
		}
	}
	return out
}

func ruleItemNames(t *testing.T, item interface{}) []string {
	t.Helper()
	switch items := item.(type) {
	case []string:
		return append([]string(nil), items...)
	case []interface{}:
		names := make([]string, 0, len(items))
		for _, raw := range items {
			name, ok := raw.(string)
			require.True(t, ok)
			names = append(names, name)
		}
		return names
	case string:
		return []string{items}
	default:
		t.Fatalf("rule item type %T", item)
		return nil
	}
}
