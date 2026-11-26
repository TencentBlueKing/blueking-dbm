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
	"crypto/md5"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"

	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

func TestCheckSQLFilesMd5(t *testing.T) {
	dir := t.TempDir()
	body := []byte("select 1;\n")
	if err := os.WriteFile(filepath.Join(dir, "a.sql"), body, 0o644); err != nil {
		t.Fatal(err)
	}
	sum := md5.Sum(body)
	match := hex.EncodeToString(sum[:])

	reads := 0
	orig := readSQLFileMD5
	readSQLFileMD5 = func(filePath string) (string, error) {
		reads++
		return orig(filePath)
	}
	t.Cleanup(func() { readSQLFileMD5 = orig })

	empty := ExecuteSQLFileComp{Params: &ExecuteSQLFileParam{}}
	empty.taskdir = dir
	if err := empty.checkSQLFilesMd5(); err != nil {
		t.Fatalf("empty map should continue, got %v", err)
	}
	if reads != 0 {
		t.Fatalf("empty map hashed %d times, want 0", reads)
	}

	okComp := ExecuteSQLFileComp{
		Params: &ExecuteSQLFileParam{
			SqlFilesMd5:    map[string]string{"a.sql": strings.ToUpper(match), "other.sql": match},
			ExecuteObjects: []ExecuteSQLFileObj{{SQLFiles: []string{"a.sql", "a.sql"}}},
		},
	}
	okComp.taskdir = dir
	reads = 0
	if err := okComp.checkSQLFilesMd5(); err != nil {
		t.Fatalf("matching file should pass, got %v", err)
	}
	if reads != 1 {
		t.Fatalf("same file hashed %d times, want 1", reads)
	}

	bad := ExecuteSQLFileComp{
		Params: &ExecuteSQLFileParam{
			SqlFilesMd5:    map[string]string{"a.sql": "00000000000000000000000000000000"},
			ExecuteObjects: []ExecuteSQLFileObj{{SQLFiles: []string{"a.sql"}}},
		},
	}
	bad.taskdir = dir
	if err := bad.checkSQLFilesMd5(); err == nil || !strings.Contains(err.Error(), "不一致") {
		t.Fatalf("mismatch should fail, got %v", err)
	}

	missing := ExecuteSQLFileComp{
		Params: &ExecuteSQLFileParam{
			SqlFilesMd5:    map[string]string{"b.sql": match},
			ExecuteObjects: []ExecuteSQLFileObj{{SQLFiles: []string{"a.sql"}}},
		},
	}
	missing.taskdir = dir
	if err := missing.checkSQLFilesMd5(); err == nil || !strings.Contains(err.Error(), "缺失") {
		t.Fatalf("missing digest should fail, got %v", err)
	}

	illegal := ExecuteSQLFileComp{
		Params: &ExecuteSQLFileParam{
			SqlFilesMd5:    map[string]string{"a.sql": "not-an-md5"},
			ExecuteObjects: []ExecuteSQLFileObj{{SQLFiles: []string{"a.sql"}}},
		},
	}
	illegal.taskdir = dir
	if err := illegal.checkSQLFilesMd5(); err == nil || !strings.Contains(err.Error(), "非法") {
		t.Fatalf("illegal digest should fail, got %v", err)
	}

	gone := ExecuteSQLFileComp{
		Params: &ExecuteSQLFileParam{
			SqlFilesMd5:    map[string]string{"gone.sql": match},
			ExecuteObjects: []ExecuteSQLFileObj{{SQLFiles: []string{"gone.sql"}}},
		},
	}
	gone.taskdir = dir
	if err := gone.checkSQLFilesMd5(); err == nil || !strings.Contains(err.Error(), "读取SQL文件失败") {
		t.Fatalf("missing file should fail, got %v", err)
	}
}

func TestMd5MismatchStopsBeforeSedAndExecute(t *testing.T) {
	dir := t.TempDir()
	body := []byte("select 1;\n")
	if err := os.WriteFile(filepath.Join(dir, "a.sql"), body, 0o644); err != nil {
		t.Fatal(err)
	}
	comp := ExecuteSQLFileComp{
		Params: &ExecuteSQLFileParam{
			SqlFilesMd5:    map[string]string{"a.sql": "00000000000000000000000000000000"},
			ExecuteObjects: []ExecuteSQLFileObj{{SQLFiles: []string{"a.sql"}}},
			IsSpider:       true,
		},
	}
	comp.taskdir = dir
	sedCalled := false
	executeCalled := false
	err := (subcmd.Steps{
		{FunName: "Pre-Check", Func: comp.PreCheck},
		{FunName: "执行前预处理", Func: func() error { sedCalled = true; return nil }},
		{FunName: "执行导入SQL文件", Func: func() error { executeCalled = true; return nil }},
	}).Run()
	if err == nil || !strings.Contains(err.Error(), "不一致") {
		t.Fatalf("mismatch should stop the steps, got %v", err)
	}
	if sedCalled || executeCalled {
		t.Fatalf("later steps ran, sed=%v execute=%v", sedCalled, executeCalled)
	}
	got, readErr := os.ReadFile(filepath.Join(dir, "a.sql"))
	if readErr != nil {
		t.Fatal(readErr)
	}
	if string(got) != string(body) {
		t.Fatalf("sql file changed: %q", got)
	}
}

func TestEmptyMd5ContinuesToLaterSteps(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "a.sql"), []byte("select 1;\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	comp := ExecuteSQLFileComp{
		Params: &ExecuteSQLFileParam{
			ExecuteObjects: []ExecuteSQLFileObj{{SQLFiles: []string{"a.sql"}}},
		},
	}
	comp.taskdir = dir
	executeCalled := false
	if err := (subcmd.Steps{
		{FunName: "Pre-Check", Func: comp.PreCheck},
		{FunName: "执行导入SQL文件", Func: func() error { executeCalled = true; return nil }},
	}).Run(); err != nil {
		t.Fatalf("empty map should continue, got %v", err)
	}
	if !executeCalled {
		t.Fatal("empty map should reach execute")
	}
}

func TestSQLFilesMd5SurvivesPayloadJSON(t *testing.T) {
	raw := []byte(`{"general":{},"extend":{"host":"127.0.0.1","ports":[3306],"charset":"utf8","sql_files_md5":{"a.sql":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},"execute_objects":[{"sql_files":["a.sql"]}]}}`)
	var comp ExecuteSQLFileComp
	if err := json.Unmarshal(raw, &comp); err != nil {
		t.Fatal(err)
	}
	if comp.Params == nil || comp.Params.SqlFilesMd5["a.sql"] != "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" {
		t.Fatalf("md5 not parsed: %+v", comp.Params)
	}

	var omitted ExecuteSQLFileComp
	if err := json.Unmarshal([]byte(`{"extend":{"host":"127.0.0.1","charset":"utf8"}}`), &omitted); err != nil {
		t.Fatal(err)
	}
	if len(omitted.Params.SqlFilesMd5) != 0 {
		t.Fatalf("omitted key should be empty, got %+v", omitted.Params.SqlFilesMd5)
	}
}

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

func TestExecuteSQLFileComp_PreCheckEmptySkips(t *testing.T) {
	t.Parallel()
	db, mock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherRegexp))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	mock.ExpectQuery("(?i)show status like").WillReturnError(sql.ErrNoRows)

	comp := newTcIsPrimaryComp(db, 26000)
	if err := comp.checkTcIsPrimaryStatus(); err != nil {
		t.Fatalf("empty status should skip, got %v", err)
	}
	if comp.needSessionTcAdmin {
		t.Fatal("empty status should not set needSessionTcAdmin")
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestExecuteSQLFileComp_PreCheckZeroFails(t *testing.T) {
	t.Parallel()
	db, mock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherRegexp))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	mock.ExpectQuery("(?i)show status like").WillReturnRows(
		sqlmock.NewRows([]string{"Variable_name", "Value"}).AddRow("Tc_is_primary", "0"),
	)

	comp := newTcIsPrimaryComp(db, 26000)
	err = comp.checkTcIsPrimaryStatus()
	if err == nil {
		t.Fatal("expected error when Tc_is_primary=0")
	}
	if !strings.Contains(err.Error(), "tc_is_primary") && !strings.Contains(err.Error(), "Tc_is_primary") {
		t.Fatalf("error should mention tc_is_primary, got %v", err)
	}
	if !strings.Contains(err.Error(), "0") {
		t.Fatalf("error should mention value 0, got %v", err)
	}
	if !strings.Contains(err.Error(), "127.0.0.1") || !strings.Contains(err.Error(), "26000") {
		t.Fatalf("error should mention host and port, got %v", err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestExecuteSQLFileComp_PreCheckOtherFails(t *testing.T) {
	t.Parallel()
	db, mock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherRegexp))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	mock.ExpectQuery("(?i)show status like").WillReturnRows(
		sqlmock.NewRows([]string{"Variable_name", "Value"}).AddRow("Tc_is_primary", "2"),
	)

	comp := newTcIsPrimaryComp(db, 26000)
	err = comp.checkTcIsPrimaryStatus()
	if err == nil {
		t.Fatal("expected error when Tc_is_primary is neither empty nor 1")
	}
	if !strings.Contains(err.Error(), "127.0.0.1") || !strings.Contains(err.Error(), "26000") {
		t.Fatalf("error should mention host and port, got %v", err)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func TestExecuteSQLFileComp_PreCheckOnePasses(t *testing.T) {
	t.Parallel()
	db, mock, err := sqlmock.New(sqlmock.QueryMatcherOption(sqlmock.QueryMatcherRegexp))
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	mock.ExpectQuery("(?i)show status like").WillReturnRows(
		sqlmock.NewRows([]string{"Variable_name", "Value"}).AddRow("Tc_is_primary", "1"),
	)

	comp := newTcIsPrimaryComp(db, 26000)
	if err := comp.checkTcIsPrimaryStatus(); err != nil {
		t.Fatalf("Tc_is_primary=1 should pass, got %v", err)
	}
	if !comp.needSessionTcAdmin {
		t.Fatal("Tc_is_primary=1 should set needSessionTcAdmin")
	}
	if sessionTcAdminInitCommand(comp.needSessionTcAdmin) != "SET SESSION tc_admin=1" {
		t.Fatal("execute path should fill InitCommand after primary=1")
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatal(err)
	}
}

func newTcIsPrimaryComp(db *sql.DB, port int) *ExecuteSQLFileComp {
	return &ExecuteSQLFileComp{
		Params: &ExecuteSQLFileParam{Host: "127.0.0.1"},
		ExecuteSQLFileRunTimeCtx: ExecuteSQLFileRunTimeCtx{
			ports:   []int{port},
			dbConns: map[Port]*native.DbWorker{port: {Db: db}},
		},
	}
}
