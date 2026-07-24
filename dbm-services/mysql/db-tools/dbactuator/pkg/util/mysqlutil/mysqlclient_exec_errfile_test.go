/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package mysqlutil_test

import (
	"path"
	"strings"
	"testing"
	"time"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

func TestBuildExecuteErrFileBase(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name    string
		sqlfile string
		db      string
		want    string
	}{
		{
			name:    "basename with db",
			sqlfile: "a.sql",
			db:      "db1",
			want:    "a.sql.db1.err",
		},
		{
			name:    "path-like sqlfile uses basename",
			sqlfile: "scripts/install_spider.sql",
			db:      "db1",
			want:    "install_spider.sql.db1.err",
		},
		{
			name:    "empty db omits double-dot",
			sqlfile: "scripts/install_spider.sql",
			db:      "",
			want:    "install_spider.sql.err",
		},
		{
			name:    "whitespace db treated as empty",
			sqlfile: "/usr/local/mysql/scripts/install_spider.sql",
			db:      "  ",
			want:    "install_spider.sql.err",
		},
	}
	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()
			got := mysqlutil.BuildExecuteErrFileBase(tt.sqlfile, tt.db)
			if got != tt.want {
				t.Fatalf("BuildExecuteErrFileBase(%q, %q)=%q, want %q", tt.sqlfile, tt.db, got, tt.want)
			}
		})
	}
}

func TestExecuteCommandOpenErrFileFailed(t *testing.T) {
	dir := t.TempDir()
	// Linux NAME_MAX is typically 255; a 300-char basename makes OpenFile fail.
	longName := strings.Repeat("a", 300) + ".err"
	e := mysqlutil.ExecuteSqlAtLocal{
		ErrFile: path.Join(dir, longName),
	}
	err := e.ExecuteCommand("echo ok", false)
	if err == nil {
		t.Fatal("expected non-nil error when opening overlong ErrFile fails")
	}
	if !strings.Contains(err.Error(), "打开错误日志失败") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestExecuteCommandOpenErrFileOK(t *testing.T) {
	dir := t.TempDir()
	e := mysqlutil.ExecuteSqlAtLocal{
		ErrFile: path.Join(dir, "commandTest.err"),
	}
	err := e.ExecuteCommand("echo ok", false)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestExecuteCommandIgnoreStdoOpenErrFileFailed(t *testing.T) {
	dir := t.TempDir()
	longName := strings.Repeat("b", 300) + ".err"
	e := mysqlutil.ExecuteSqlAtLocal{
		ErrFile: path.Join(dir, longName),
	}
	err := e.ExecuteCommandIgnoreStdo("echo ok")
	if err == nil {
		t.Fatal("expected non-nil error when opening overlong ErrFile fails")
	}
	if !strings.Contains(err.Error(), "打开错误日志失败") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestCheckMyExecuteErrFileNameLen(t *testing.T) {
	t.Parallel()
	if len(mysqlutil.ErrLogTimestampPlaceholder) != len(time.Now().Format(cst.TimeLayoutDir)) {
		t.Fatalf("timestamp placeholder length mismatch: placeholder=%d layout=%d",
			len(mysqlutil.ErrLogTimestampPlaceholder), len(time.Now().Format(cst.TimeLayoutDir)))
	}

	// {sqlfile}.{db}.{14}.{err4} = 255 => sqlfile+db = 255-1-1-14-4 = 235
	okSQL := strings.Repeat("a", 171)
	okDB := strings.Repeat("b", 64) // 171+1+64+1+14+4 = 255
	if err := mysqlutil.CheckMyExecuteErrFileNameLen(okSQL, okDB); err != nil {
		t.Fatalf("expected pass at NAME_MAX boundary, got %v", err)
	}

	tooLongSQL := strings.Repeat("a", 172)
	if err := mysqlutil.CheckMyExecuteErrFileNameLen(tooLongSQL, okDB); err == nil {
		t.Fatal("expected error when err base exceeds NAME_MAX")
	} else if !strings.Contains(err.Error(), "err log 文件名过长") {
		t.Fatalf("unexpected error: %v", err)
	}

	// open-area schema style: {schema}.sql.{newdb}.new.{newdb}.{ts}.err
	// len = len(schema) + 2*len(newdb) + 29; with newdb=64 need schema > 98 to exceed 255
	schema := strings.Repeat("s", 100)
	newDB := strings.Repeat("d", 64)
	schemaFile := schema + ".sql." + newDB + ".new"
	if err := mysqlutil.CheckMyExecuteErrFileNameLen(schemaFile, newDB); err == nil {
		t.Fatal("expected error for long open-area schema err file name")
	}
}
