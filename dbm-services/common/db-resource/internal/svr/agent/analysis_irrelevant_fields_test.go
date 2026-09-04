/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package agent

import "testing"

func TestSqlMentionsIrrelevantColumns(t *testing.T) {
	if !sqlMentionsIrrelevantColumns("SELECT consume_time, is_idle FROM tb_rp_detail") {
		t.Fatal("should detect consume_time / is_idle")
	}
	if sqlMentionsIrrelevantColumns("SELECT city, status FROM tb_rp_detail WHERE status='Unused'") {
		t.Fatal("match columns should not be flagged")
	}
}

func TestStripIrrelevantColumns(t *testing.T) {
	cols := []string{"bk_host_id", "status", "consume_time", "is_idle", "is_init", "city"}
	rows := []interface{}{
		map[string]interface{}{
			"bk_host_id":   4447536,
			"status":       "Unused",
			"consume_time": "1970-01-01T08:00:01",
			"is_idle":      0,
			"is_init":      0,
			"city":         "香港",
		},
	}
	gotCols, gotRows, stripped := stripIrrelevantColumns(cols, rows)
	if !stripped {
		t.Fatal("expected strip")
	}
	wantCols := []string{"bk_host_id", "status", "city"}
	if len(gotCols) != len(wantCols) {
		t.Fatalf("cols=%v want %v", gotCols, wantCols)
	}
	for i := range wantCols {
		if gotCols[i] != wantCols[i] {
			t.Fatalf("cols=%v want %v", gotCols, wantCols)
		}
	}
	m := gotRows[0].(map[string]interface{})
	if _, ok := m["consume_time"]; ok {
		t.Fatal("consume_time should be stripped")
	}
	if _, ok := m["is_idle"]; ok {
		t.Fatal("is_idle should be stripped")
	}
	if m["status"] != "Unused" || m["city"] != "香港" {
		t.Fatalf("kept fields wrong: %v", m)
	}
}

func TestAppendAnalysisWarningDedup(t *testing.T) {
	once := appendAnalysisWarning("", analysisIrrelevantWarning)
	twice := appendAnalysisWarning(once, analysisIrrelevantWarning)
	if once != twice {
		t.Fatal("same warning should not be appended twice")
	}
}
