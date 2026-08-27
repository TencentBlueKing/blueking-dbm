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
	"encoding/json"
	"strings"
	"testing"
)

func TestCheckSQLFileNameLength(t *testing.T) {
	t.Parallel()

	exactMax := strings.Repeat("a", MaxSQLFileNameLen-4) + ".sql"
	tooLong := strings.Repeat("a", MaxSQLFileNameLen-3) + ".sql"
	tooLong2 := strings.Repeat("b", MaxSQLFileNameLen+1) + ".sql"

	tests := []struct {
		name    string
		files   []string
		wantErr bool
		wantMsg string
	}{
		{
			name:    "exact max length passes",
			files:   []string{exactMax},
			wantErr: false,
		},
		{
			name:    "one over limit fails",
			files:   []string{tooLong},
			wantErr: true,
			wantMsg: "SQL文件名过长",
		},
		{
			name:    "multiple over limit reports all",
			files:   []string{tooLong, tooLong2},
			wantErr: true,
			wantMsg: "SQL文件名过长",
		},
		{
			name:    "basename used for path-like input",
			files:   []string{"/tmp/" + tooLong},
			wantErr: true,
			wantMsg: "SQL文件名过长",
		},
		{
			name:    "short name passes",
			files:   []string{"ok.sql"},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			err := checkSQLFileNameLength(tt.files)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error, got nil")
				}
				if !strings.Contains(err.Error(), tt.wantMsg) {
					t.Fatalf("error %q should contain %q", err.Error(), tt.wantMsg)
				}
				if !strings.Contains(err.Error(), "上限") {
					t.Fatalf("error %q should mention limit", err.Error())
				}
				if len(tt.files) > 1 {
					for _, f := range tt.files {
						base := f
						if i := strings.LastIndex(f, "/"); i >= 0 {
							base = f[i+1:]
						}
						if !strings.Contains(err.Error(), base) {
							t.Fatalf("error %q should mention file %s", err.Error(), base)
						}
					}
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})
	}
}

func TestCheckSQLFileNameLengthViaComp(t *testing.T) {
	t.Parallel()
	tooLong := strings.Repeat("x", MaxSQLFileNameLen+1) + ".sql"
	comp := &ExecuteSQLFileComp{
		Params: &ExecuteSQLFileParam{
			ExecuteObjects: []ExecuteSQLFileObj{
				{SQLFiles: []string{tooLong}},
			},
		},
	}
	err := comp.CheckSQLFileNameLength()
	if err == nil {
		t.Fatal("expected error for overlong sql file name")
	}
}

func TestSQLFileExecResultJSONIncludesDBName(t *testing.T) {
	t.Parallel()
	r := SQLFileExecResult{
		Port:     3306,
		SQLFile:  "a.sql",
		DBName:   "db1",
		Duration: 3,
		Success:  true,
	}
	b, err := json.Marshal(r)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	got := string(b)
	if !strings.Contains(got, `"sql_file":"a.sql"`) {
		t.Fatalf("json should contain sql_file, got %s", got)
	}
	if !strings.Contains(got, `"db_name":"db1"`) {
		t.Fatalf("json should contain db_name, got %s", got)
	}
	if strings.Contains(got, `"sql_file_path"`) {
		t.Fatalf("json should not contain local sql_file_path, got %s", got)
	}
	if strings.Contains(got, `"Port"`) || strings.Contains(got, `"port"`) {
		t.Fatalf("Port is json:\"-\" and should be omitted, got %s", got)
	}
}
