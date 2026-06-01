/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlutil

import (
	"strings"
	"testing"
)

func TestShellSingleQuote(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
	}{
		{
			name: "no single quote",
			in:   "id > 100",
			want: `'id > 100'`,
		},
		{
			name: "value wrapped by single quote",
			in:   "'2026-6-1'",
			want: `''\''2026-6-1'\'''`,
		},
		{
			name: "where with date literal",
			in:   "create_time > '2026-6-1'",
			want: `'create_time > '\''2026-6-1'\'''`,
		},
		{
			name: "where with double quote date literal",
			in:   `create_time > "2026-6-1"`,
			want: `'create_time > "2026-6-1"'`,
		},
		{
			name: "shell metachars stay literal",
			in:   "a=`whoami` and b=$HOME",
			want: "'a=`whoami` and b=$HOME'",
		},
		{
			name: "multiple single quotes",
			in:   "a='x' and b='y'",
			want: `'a='\''x'\'' and b='\''y'\'''`,
		},
		{
			name: "empty string",
			in:   "",
			want: `''`,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := shellSingleQuote(c.in)
			if got != c.want {
				t.Fatalf("shellSingleQuote(%q) = %q, want %q", c.in, got, c.want)
			}
		})
	}
}

// TestGetDumpCmdWhereEscape 验证带单引号的 where 条件被正确转义，
// 不会出现内部引号提前闭合导致日期字面量被 shell 吞掉的问题。
func TestGetDumpCmdWhereEscape(t *testing.T) {
	m := &MySQLDumper{
		DumpCmdFile:  "/usr/bin/mysqldump",
		Ip:           "127.0.0.1",
		Port:         3306,
		DbBackupUser: "user",
		DbBackupPwd:  "pwd",
		DbNames:      []string{"testdb"},
		Where:        "create_time > '2026-6-1'",
	}
	cmd := m.getDumpCmd("/tmp/out.sql", "/tmp/out.err", "", false)

	wantWhere := ` --where='create_time > '\''2026-6-1'\'''`
	if !strings.Contains(cmd, wantWhere) {
		t.Fatalf("dump cmd 未正确转义 where 条件\n got: %s\n want contains: %s", cmd, wantWhere)
	}

	// 确认不会出现错误的裸引号形式（旧 bug 产物）
	badWhere := ` --where='create_time > '2026-6-1''`
	if strings.Contains(cmd, badWhere) {
		t.Fatalf("dump cmd 仍存在旧的错误引号拼接: %s", cmd)
	}
}

// TestGetDumpCmdWhereDoubleQuote 验证 where 使用双引号时,双引号被原样保留,
// 不会被 shell 吞掉。
func TestGetDumpCmdWhereDoubleQuote(t *testing.T) {
	m := &MySQLDumper{
		DumpCmdFile:  "/usr/bin/mysqldump",
		Ip:           "127.0.0.1",
		Port:         3306,
		DbBackupUser: "user",
		DbBackupPwd:  "pwd",
		DbNames:      []string{"testdb"},
		Where:        `create_time > "2026-6-1"`,
	}
	cmd := m.getDumpCmd("/tmp/out.sql", "/tmp/out.err", "", false)

	wantWhere := ` --where='create_time > "2026-6-1"'`
	if !strings.Contains(cmd, wantWhere) {
		t.Fatalf("dump cmd 未正确保留双引号 where 条件\n got: %s\n want contains: %s", cmd, wantWhere)
	}
}

// TestGetDumpCmdWhereEmpty 验证 where 为空时不追加 --where 参数。
func TestGetDumpCmdWhereEmpty(t *testing.T) {
	m := &MySQLDumper{
		DumpCmdFile:  "/usr/bin/mysqldump",
		Ip:           "127.0.0.1",
		Port:         3306,
		DbBackupUser: "user",
		DbBackupPwd:  "pwd",
		DbNames:      []string{"testdb"},
		Where:        "",
	}
	cmd := m.getDumpCmd("/tmp/out.sql", "/tmp/out.err", "", false)
	if strings.Contains(cmd, "--where") {
		t.Fatalf("where 为空时不应出现 --where 参数: %s", cmd)
	}
}
