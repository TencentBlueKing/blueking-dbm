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
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

const (
	extraMsgChangeColumn   = "变更字段类型会阻塞当前表的读写！！！"
	extraMsgDropPrimary    = "单独删除主键会重建表且不允许并发 DML，会阻塞当前表的读写！！！"
	extraMsgConvertCharset = "CONVERT TO CHARACTER SET 会重建表且不允许并发 DML，会阻塞当前表的读写！！！"
)

func newHighRiskTypeRule(extra map[string]string) *RuleItem {
	rule := &RuleItem{
		Expr: " Val in Item ",
		Item: []string{
			"drop_column", "drop_key", "change_column", "rename_table", "rename_key", HighRiskConvertCharset,
		},
		Desc:            "高危变更类型",
		Suggestion:      "请在变更表时避免使用高危变更类型",
		ExtraMessageMap: extra,
	}
	return rule
}

func TestParseExtraMessageMap_ChangeColumn(t *testing.T) {
	rule := newHighRiskTypeRule(map[string]string{
		"change_column": extraMsgChangeColumn,
	})
	require.NoError(t, rule.compile())

	r := &CheckerResult{ObjName: "t1"}
	r.Parse(rule, "change_column", "字段: foo")

	require.Len(t, r.RiskWarns, 1)
	msg := r.RiskWarns[0]
	assert.True(t, strings.HasPrefix(msg, extraMsgChangeColumn), "extra_message 应置于告警最前: %s", msg)
	assert.Contains(t, msg, "高危变更类型")
	assert.Contains(t, msg, "change_column")
	assert.Contains(t, msg, "字段: foo")
	assert.Contains(t, msg, "请在变更表时避免使用高危变更类型")
}

func TestParseExtraMessageMap_DropPrimary(t *testing.T) {
	rule := newHighRiskTypeRule(map[string]string{
		"drop_primary": extraMsgDropPrimary,
	})
	require.NoError(t, rule.compile())

	r := &CheckerResult{ObjName: "t1"}
	// 匹配值仍是 drop_key；额外文案按 drop_primary 查
	r.ParseWithExtraKey(rule, "drop_key", "drop_primary", "主键")

	require.Len(t, r.RiskWarns, 1)
	msg := r.RiskWarns[0]
	assert.True(t, strings.HasPrefix(msg, extraMsgDropPrimary), "extra_message 应置于告警最前: %s", msg)
	assert.Contains(t, msg, "当前值:drop_key")
	assert.Contains(t, msg, "主键")
	assert.NotContains(t, msg, "当前值:drop_primary")
}

func TestParseExtraMessageMap_DropColumnNoExtra(t *testing.T) {
	rule := newHighRiskTypeRule(map[string]string{
		"change_column": extraMsgChangeColumn,
		"drop_primary":  extraMsgDropPrimary,
	})
	require.NoError(t, rule.compile())

	r := &CheckerResult{ObjName: "t1"}
	r.Parse(rule, "drop_column", "字段: bar")

	require.Len(t, r.RiskWarns, 1)
	msg := r.RiskWarns[0]
	assert.Contains(t, msg, "字段: bar")
	assert.NotContains(t, msg, extraMsgChangeColumn)
	assert.NotContains(t, msg, extraMsgDropPrimary)
}

func TestParseExtraMessageMap_EmptyMap(t *testing.T) {
	rule := newHighRiskTypeRule(nil)
	require.NoError(t, rule.compile())

	r := &CheckerResult{ObjName: "t1"}
	r.Parse(rule, "change_column", "")

	require.Len(t, r.RiskWarns, 1)
	msg := r.RiskWarns[0]
	assert.Contains(t, msg, "高危变更类型")
	assert.NotContains(t, msg, "变更字段类型会全局锁表！！！")
	// 空 additional/extra 不应留下多余空行噪音：去掉首尾空白后不应以换行开头的连续空段破坏可读性
	assert.False(t, strings.Contains(msg, "\n\n\n"))
}

func TestAlterCommandRiskObjectDesc(t *testing.T) {
	cases := []struct {
		name string
		cmd  AlterCommand
		want string
	}{
		{
			name: "change_column",
			cmd: AlterCommand{
				Type:   "change_column",
				ColDef: ColDef{ColName: "foo"},
			},
			want: "字段: foo",
		},
		{
			name: "drop_column",
			cmd: AlterCommand{
				Type:   AlterTypeDropColumn,
				ColDef: ColDef{ColName: "bar"},
			},
			want: "字段: bar",
		},
		{
			name: "rename_key",
			cmd: AlterCommand{
				Type:       "rename_key",
				OldKeyName: "idx_a",
				NewKeyName: "idx_b",
			},
			want: "索引: idx_a→idx_b",
		},
		{
			name: "drop_key",
			cmd: AlterCommand{
				Type:   AlterTypeDropKey,
				KeyDef: KeyDef{KeyName: "idx_c"},
			},
			want: "索引: idx_c",
		},
		{
			name: "drop_primary",
			cmd: AlterCommand{
				Type:        AlterTypeDropKey,
				DropPrimary: true,
			},
			want: "主键",
		},
		{
			name: "rename_table",
			cmd: AlterCommand{
				Type:      "rename_table",
				TableName: "new_t",
			},
			want: "表: new_t",
		},
		{
			name: "convert_charset",
			cmd: AlterCommand{
				Type:   AlterTypeTableOptions,
				Action: AlterActionConvert,
			},
			want: "字符集转换",
		},
		{
			name: "default_charset_no_desc",
			cmd: AlterCommand{
				Type:   AlterTypeTableOptions,
				Action: "default",
			},
			want: "",
		},
		{
			name: "empty",
			cmd:  AlterCommand{Type: "change_column"},
			want: "",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			assert.Equal(t, tc.want, tc.cmd.RiskObjectDesc())
		})
	}
}

func TestAlterCommandExtraMessageKey(t *testing.T) {
	assert.Equal(t, "drop_primary", AlterCommand{Type: AlterTypeDropKey, DropPrimary: true}.ExtraMessageKey())
	assert.Equal(t, "drop_key", AlterCommand{Type: AlterTypeDropKey}.ExtraMessageKey())
	assert.Equal(t, "change_column", AlterCommand{Type: "change_column"}.ExtraMessageKey())
	assert.Equal(t, HighRiskConvertCharset, AlterCommand{
		Type: AlterTypeTableOptions, Action: AlterActionConvert,
	}.ExtraMessageKey())
	assert.Equal(t, AlterTypeTableOptions, AlterCommand{
		Type: AlterTypeTableOptions, Action: "default",
	}.ExtraMessageKey())
}

func TestAlterCommandHighRiskTypeVal(t *testing.T) {
	assert.Equal(t, HighRiskConvertCharset, AlterCommand{
		Type: AlterTypeTableOptions, Action: AlterActionConvert,
	}.HighRiskTypeVal())
	assert.Equal(t, AlterTypeTableOptions, AlterCommand{
		Type: AlterTypeTableOptions, Action: "default",
	}.HighRiskTypeVal())
	assert.Equal(t, "drop_key", AlterCommand{Type: AlterTypeDropKey, DropPrimary: true}.HighRiskTypeVal())
}

func TestAlterTableChecker_HighRiskTypeExtraMessage(t *testing.T) {
	if R == nil || R.AlterTableRule.HighRiskType == nil {
		t.Skip("rules not loaded")
	}
	// 确保测试使用带 extra_message_map 的规则（与 rule.yaml 一致）
	orig := R.AlterTableRule.HighRiskType
	rule := newHighRiskTypeRule(map[string]string{
		"change_column":        extraMsgChangeColumn,
		"drop_primary":         extraMsgDropPrimary,
		HighRiskConvertCharset: extraMsgConvertCharset,
	})
	require.NoError(t, rule.compile())
	R.AlterTableRule.HighRiskType = rule
	defer func() { R.AlterTableRule.HighRiskType = orig }()

	result := AlterTableResult{
		TableName: "t1",
		AlterCommands: []AlterCommand{
			{
				Type:   "change_column",
				ColDef: ColDef{ColName: "foo", DataType: "int"},
			},
			{
				Type:        AlterTypeDropKey,
				DropPrimary: true,
			},
			{
				Type:   AlterTypeTableOptions,
				Action: AlterActionConvert,
				TableOptions: []TableOption{
					{Key: "character_set", Value: "utf8mb4"},
				},
			},
			{
				// DEFAULT CHARACTER SET：不应命中 HighRiskType
				Type:   AlterTypeTableOptions,
				Action: "default",
				TableOptions: []TableOption{
					{Key: "character_set", Value: "utf8mb4"},
				},
			},
		},
	}
	cr := result.Checker("5.7")
	require.NotNil(t, cr)
	joined := strings.Join(cr.RiskWarns, "\n")
	assert.Contains(t, joined, "字段: foo")
	assert.Contains(t, joined, extraMsgChangeColumn)
	assert.Contains(t, joined, "主键")
	assert.Contains(t, joined, "当前值:drop_key")
	assert.Contains(t, joined, extraMsgDropPrimary)
	assert.NotContains(t, joined, "当前值:drop_primary")
	assert.Contains(t, joined, "当前值:convert_charset")
	assert.Contains(t, joined, "字符集转换")
	assert.Contains(t, joined, extraMsgConvertCharset)
	assert.NotContains(t, joined, "当前值:table_options")
}

func TestYamlExtraMessageMapLoad(t *testing.T) {
	if R == nil || R.AlterTableRule.HighRiskType == nil {
		t.Skip("rules not loaded")
	}
	msg, ok := R.AlterTableRule.HighRiskType.ExtraMessageMap["change_column"]
	if !ok || msg == "" {
		// 测试环境可能加载到 minimal rule，此时跳过
		t.Skip("extra_message_map not loaded from rule.yaml")
	}
	assert.Equal(t, extraMsgChangeColumn, msg)
	assert.Equal(t, extraMsgDropPrimary, R.AlterTableRule.HighRiskType.ExtraMessageMap["drop_primary"])
	assert.Equal(t, extraMsgConvertCharset, R.AlterTableRule.HighRiskType.ExtraMessageMap[HighRiskConvertCharset])
}
