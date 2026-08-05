/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package injectrule

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestEvaluate(t *testing.T) {
	t.Parallel()

	cases := []struct {
		name                   string
		lines                  []ParseLine
		judgeSubqueryDiffTable bool
		wantInject             bool
		wantReasonContains     []string
		wantReasonExact        string
	}{
		{
			name: "clean select",
			lines: []ParseLine{
				{Command: "select", QueryString: "SELECT id FROM t1 WHERE id = 1"},
			},
			wantInject: false,
		},
		{
			name: "multi statement",
			lines: []ParseLine{
				{Command: "select", QueryString: "SELECT 1"},
				{Command: "select", QueryString: "SELECT 2"},
			},
			wantInject:         true,
			wantReasonContains: []string{"多语句"},
		},
		{
			name: "union",
			lines: []ParseLine{
				{Command: "select", QueryString: "SELECT id FROM t1 UNION SELECT password FROM users"},
			},
			wantInject:         true,
			wantReasonContains: []string{"UNION"},
		},
		{
			name: "sleep",
			lines: []ParseLine{
				{Command: "select", QueryString: "SELECT * FROM t1 WHERE id=1 AND SLEEP(5)"},
			},
			wantInject:         true,
			wantReasonContains: []string{"SLEEP"},
		},
		{
			name: "into outfile",
			lines: []ParseLine{
				{Command: "select", QueryString: "SELECT * FROM t1 INTO OUTFILE '/tmp/a.txt'"},
			},
			wantInject:         true,
			wantReasonContains: []string{"OUTFILE"},
		},
		{
			name: "load_file",
			lines: []ParseLine{
				{Command: "select", QueryString: "SELECT LOAD_FILE('/etc/passwd')"},
			},
			wantInject:         true,
			wantReasonContains: []string{"LOAD_FILE"},
		},
		{
			name: "inline hash comment",
			lines: []ParseLine{
				{Command: "update", QueryString: "UPDATE t1 SET a=1 WHERE id=1 # and admin=1"},
			},
			wantInject:         true,
			wantReasonContains: []string{"行内注释"},
		},
		{
			name: "tautology or 1=1",
			lines: []ParseLine{
				{Command: "select", QueryString: "SELECT * FROM t1 WHERE name='x' OR 1=1"},
			},
			wantInject:         true,
			wantReasonContains: []string{"恒真"},
		},
		{
			name: "same table subquery with flag on - not inject",
			lines: []ParseLine{
				{
					Command:     "select",
					HasSubQuery: true,
					QueryString: "SELECT * FROM t1 WHERE id IN (SELECT id FROM t1 WHERE a=1)",
					TableReferences: []TableReference{
						{TableName: "t1"},
						{TableName: "t1"},
					},
				},
			},
			judgeSubqueryDiffTable: true,
			wantInject:             false,
		},
		{
			name: "diff table subquery with flag on - inject",
			lines: []ParseLine{
				{
					Command:     "select",
					HasSubQuery: true,
					QueryString: "SELECT * FROM t1 WHERE id IN (SELECT id FROM t2)",
					TableReferences: []TableReference{
						{TableName: "t1"},
						{TableName: "t2"},
					},
				},
			},
			judgeSubqueryDiffTable: true,
			wantInject:             true,
			wantReasonContains:     []string{"不同表", "t1", "t2"},
		},
		{
			name: "diff table subquery with flag off - not inject",
			lines: []ParseLine{
				{
					Command:     "select",
					HasSubQuery: true,
					QueryString: "SELECT * FROM t1 WHERE id IN (SELECT id FROM t2)",
					TableReferences: []TableReference{
						{TableName: "t1"},
						{TableName: "t2"},
					},
				},
			},
			judgeSubqueryDiffTable: false,
			wantInject:             false,
		},
		{
			name: "update subquery with flag on - not inject by rule B",
			lines: []ParseLine{
				{
					Command:     "update",
					HasSubQuery: true,
					QueryString: "UPDATE t1 SET a=1 WHERE id IN (SELECT id FROM t2)",
				},
			},
			judgeSubqueryDiffTable: true,
			wantInject:             false,
			wantReasonExact:        "子查询不同表规则仅支持 SELECT，当前语句未按该规则判定为注入",
		},
		{
			name: "cross db same table name treated distinct when both have db",
			lines: []ParseLine{
				{
					Command:     "select",
					HasSubQuery: true,
					QueryString: "SELECT * FROM db1.t1 WHERE id IN (SELECT id FROM db2.t1)",
					TableReferences: []TableReference{
						{DbName: "db1", TableName: "t1"},
						{DbName: "db2", TableName: "t1"},
					},
				},
			},
			judgeSubqueryDiffTable: true,
			wantInject:             true,
			wantReasonContains:     []string{"不同表"},
		},
	}

	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got := Evaluate(tc.lines, tc.judgeSubqueryDiffTable)
			assert.Equal(t, tc.wantInject, got.IsInject, "reason=%s", got.Reason)
			if tc.wantReasonExact != "" {
				assert.Equal(t, tc.wantReasonExact, got.Reason)
			}
			for _, part := range tc.wantReasonContains {
				assert.Contains(t, got.Reason, part)
			}
			if !tc.wantInject && tc.wantReasonExact == "" {
				assert.Empty(t, got.Reason)
			}
		})
	}
}

func TestUniqueTableRefs(t *testing.T) {
	t.Parallel()
	refs := UniqueTableRefs([]TableReference{
		{TableName: "T1"},
		{TableName: "t1"},
		{DbName: "db1", TableName: "t2"},
		{TableName: ""},
	})
	assert.Equal(t, []string{"t1", "db1.t2"}, refs)
}
