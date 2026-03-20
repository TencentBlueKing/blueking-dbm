/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
package mysql

import (
	"testing"
)

func TestReplaceMultiValuesWithCount(t *testing.T) {
	tests := []struct {
		name                string
		input               string
		expectedWithComment string
		expectedForHash     string
	}{
		{
			name:                "single IN clause with 3 items",
			input:               "SELECT * FROM t WHERE col1 IN (?,?,?)",
			expectedWithComment: "SELECT * FROM t WHERE col1 IN (?+/*omitted 3 items ...*/)",
			expectedForHash:     "SELECT * FROM t WHERE col1 IN (?+)",
		},
		{
			name:                "multiple IN clauses with different counts",
			input:               "SELECT * FROM t WHERE col1 IN (?,?,?) AND col2 IN (?,?)",
			expectedWithComment: "SELECT * FROM t WHERE col1 IN (?+/*omitted 3 items ...*/) AND col2 IN (?+/*omitted 2 items ...*/)",
			expectedForHash:     "SELECT * FROM t WHERE col1 IN (?+) AND col2 IN (?+)",
		},
		{
			name:                "VALUES clause",
			input:               "INSERT INTO t VALUES (?,?,?),(?,?,?),(?,?,?)",
			expectedWithComment: "INSERT INTO t VALUES (?+/*omitted 9 items ...*/)",
			expectedForHash:     "INSERT INTO t VALUES (?+)",
		},
		{
			name:                "mixed IN and VALUES",
			input:               "INSERT INTO t SELECT * FROM t2 WHERE id IN (?,?,?,?) VALUES (?,?)",
			expectedWithComment: "INSERT INTO t SELECT * FROM t2 WHERE id IN (?+/*omitted 4 items ...*/) VALUES (?+/*omitted 2 items ...*/)",
			expectedForHash:     "INSERT INTO t SELECT * FROM t2 WHERE id IN (?+) VALUES (?+)",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotWithComment, gotForHash := replaceMultiValuesWithCount(tt.input)
			if gotWithComment != tt.expectedWithComment {
				t.Errorf("withComment = %v, want %v", gotWithComment, tt.expectedWithComment)
			}
			if gotForHash != tt.expectedForHash {
				t.Errorf("forHash = %v, want %v", gotForHash, tt.expectedForHash)
			}
		})
	}
}
