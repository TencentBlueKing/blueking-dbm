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
	"archive/zip"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"io"
	"os"
	"path"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
)

type fakeExportConn struct {
	execs    []string
	queries  []string
	result   queryResult
	failOn   string
	writeErr error
}

func (f *fakeExportConn) Exec(ctx context.Context, query string) error {
	f.execs = append(f.execs, query)
	return nil
}

func (f *fakeExportConn) WriteQueryCSV(ctx context.Context, query, filePath string) error {
	f.queries = append(f.queries, query)
	if f.failOn != "" && strings.Contains(query, f.failOn) {
		return os.ErrInvalid
	}
	if f.writeErr != nil {
		if err := os.WriteFile(filePath, []byte("partial"), 0o644); err != nil {
			return err
		}
		return f.writeErr
	}
	return writeCSV(filePath, f.result)
}

func (f *fakeExportConn) Close() error { return nil }

func writeSQL(t *testing.T, body string) (string, string) {
	t.Helper()
	filePath := filepath.Join(t.TempDir(), "a.sql")
	if err := os.WriteFile(filePath, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256([]byte(body))
	return filePath, hex.EncodeToString(sum[:])
}

func newSQLComp(t *testing.T, body, format string) *DbConsoleDumpComp {
	t.Helper()
	sqlPath, digest := writeSQL(t, body)
	work := t.TempDir()
	comp := &DbConsoleDumpComp{
		GeneralParam: &components.GeneralParam{},
		Params: DbConsoleDumpParam{
			Host:         "127.0.0.1",
			Port:         3306,
			CharSet:      "utf8mb4",
			ZipFileName:  "dump_job.zip",
			ExportMode:   exportModeSQL,
			ResultFormat: format,
			SqlLocalPath: sqlPath,
			SqlSha256:    digest,
		},
	}
	comp.GeneralParam.RuntimeAccountParam.AdminUser = "reader"
	comp.GeneralParam.RuntimeAccountParam.AdminPwd = "secret"
	comp.charset = "gbk"
	comp.backupDir = filepath.Join(work, "dbm_console_dump", "dump_job")
	if err := os.MkdirAll(comp.backupDir, 0o750); err != nil {
		t.Fatal(err)
	}
	return comp
}

func useFakes(t *testing.T, txt txtClientFunc, open openConnFunc, lines []exportStatement) {
	t.Helper()
	oldTxt, oldParse, oldOpen := runTxtClient, parseExportStatements, openExportConn
	t.Cleanup(func() {
		runTxtClient = oldTxt
		parseExportStatements = oldParse
		openExportConn = oldOpen
	})
	if txt != nil {
		runTxtClient = txt
	}
	parseExportStatements = func(sqlFile, version, clusterType string) ([]exportStatement, error) {
		return lines, nil
	}
	if open != nil {
		openExportConn = open
	}
}

func forbidTxtParse(t *testing.T) {
	t.Helper()
	parseExportStatements = func(sqlFile, version, clusterType string) ([]exportStatement, error) {
		t.Fatalf("txt export parsed %s", sqlFile)
		return nil, nil
	}
}

func readTxt(t *testing.T, in io.Reader) string {
	t.Helper()
	raw, err := io.ReadAll(in)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}

func zipNames(t *testing.T, zipPath string) []string {
	t.Helper()
	reader, err := zip.OpenReader(zipPath)
	if err != nil {
		t.Fatal(err)
	}
	defer reader.Close()
	var names []string
	for _, file := range reader.File {
		names = append(names, file.Name)
	}
	return names
}

func TestDbConsoleDumpSqlTableModeKeepsMysqldump(t *testing.T) {
	comp := &DbConsoleDumpComp{}
	if comp.isSQLExport() {
		t.Fatal("empty mode is table export")
	}
	comp.Params.ExportMode = "table"
	if comp.isSQLExport() {
		t.Fatal("table mode must stay on mysqldump")
	}
	dumpCmd := path.Join(cst.MysqldInstallPath, "bin", "mysqldump")
	if !strings.Contains(dumpCmd, "mysqldump") {
		t.Fatalf("dump command %s", dumpCmd)
	}
}

func TestDbConsoleDumpSqlTxtOneFile(t *testing.T) {
	comp := newSQLComp(t, "SELECT 1;\nSELECT 2;\n", resultFormatTxt)
	var calls int
	var stdin string
	useFakes(t, func(argv []string, in io.Reader, outPath string) error {
		calls++
		stdin = readTxt(t, in)
		return os.WriteFile(outPath, []byte("1 row in set\n2 rows in set\n"), 0o644)
	}, nil, nil)
	forbidTxtParse(t)
	if err := comp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	if calls != 1 {
		t.Fatalf("client calls %d", calls)
	}
	if stdin != "SELECT 1;\nSELECT 2;\n" {
		t.Fatalf("stdin %s", stdin)
	}
	names := zipNames(t, filepath.Join(comp.backupDir, "dump_job.zip"))
	if len(names) != 1 || names[0] != queryResultFileName {
		t.Fatalf("zip names %v", names)
	}
	body, err := os.ReadFile(filepath.Join(comp.backupDir, queryResultFileName))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(body), "rows in set") {
		t.Fatalf("result %s", body)
	}
}

func TestDbConsoleDumpSqlTxtStdinIsRawFile(t *testing.T) {
	body := "SELECT 1;\nDROPPED_BYTES\n"
	comp := newSQLComp(t, body, resultFormatTxt)
	var stdin string
	var calls int
	useFakes(t, func(argv []string, in io.Reader, outPath string) error {
		calls++
		stdin = readTxt(t, in)
		return os.WriteFile(outPath, []byte("1 row in set\n"), 0o644)
	}, nil, nil)
	forbidTxtParse(t)
	if err := comp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	if calls != 1 {
		t.Fatalf("calls %d", calls)
	}
	if stdin != body {
		t.Fatalf("stdin %s", stdin)
	}
}

func TestDbConsoleDumpSqlCsvFiles(t *testing.T) {
	comp := newSQLComp(t, "USE app;\nSELECT 1;\nSELECT 2;\n", resultFormatCSV)
	fake := &fakeExportConn{result: queryResult{Columns: []string{"id"}, Types: []string{"INT"}, Rows: [][]any{{1}}}}
	var opened int
	useFakes(t, nil, func(dsn string) (exportConn, error) {
		opened++
		if !strings.Contains(dsn, "charset=utf8mb4") || strings.Contains(dsn, "multiStatements=true") {
			t.Fatalf("dsn %s", dsn)
		}
		return fake, nil
	}, []exportStatement{
		{QueryID: 1, Command: "change_db", QueryString: "USE app;"},
		{QueryID: 2, Command: "select", QueryString: "SELECT 1;"},
		{QueryID: 3, Command: "select", QueryString: "SELECT 2;"},
	})
	if err := comp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	if opened != 1 {
		t.Fatalf("opened %d", opened)
	}
	names := zipNames(t, filepath.Join(comp.backupDir, "dump_job.zip"))
	joined := strings.Join(names, ",")
	if !strings.Contains(joined, "002.csv") || !strings.Contains(joined, "003.csv") || strings.Contains(joined, "001.csv") {
		t.Fatalf("zip %v", names)
	}
	raw, err := os.ReadFile(filepath.Join(comp.backupDir, "002.csv"))
	if err != nil {
		t.Fatal(err)
	}
	if len(raw) < 3 || raw[0] != 0xEF || raw[1] != 0xBB || raw[2] != 0xBF {
		t.Fatalf("bom %x", raw[:3])
	}
}

func TestDbConsoleDumpSqlFailureSkipsUpload(t *testing.T) {
	comp := newSQLComp(t, "SELECT 1;\nSELECT bad;\n", resultFormatCSV)
	uploaded := false
	comp.sqlUpload = func() error {
		uploaded = true
		return nil
	}
	fake := &fakeExportConn{failOn: "bad", result: queryResult{Columns: []string{"id"}, Types: []string{"INT"}, Rows: [][]any{{1}}}}
	useFakes(t, nil, func(dsn string) (exportConn, error) { return fake, nil }, []exportStatement{
		{QueryID: 1, Command: "select", QueryString: "SELECT 1;"},
		{QueryID: 2, Command: "select", QueryString: "SELECT bad;"},
	})
	if err := comp.runSQLExport(); err == nil {
		t.Fatal("expected error")
	}
	if uploaded {
		t.Fatal("upload ran")
	}
	if _, err := os.Stat(filepath.Join(comp.backupDir, "dump_job.zip")); !os.IsNotExist(err) {
		t.Fatal("zip should be absent")
	}
	if _, err := os.Stat(filepath.Join(comp.backupDir, "001.csv")); !os.IsNotExist(err) {
		t.Fatal("first csv should be deleted")
	}
}

func TestDbConsoleDumpSqlWorkDir(t *testing.T) {
	comp := &DbConsoleDumpComp{Params: DbConsoleDumpParam{ZipFileName: "dump_job.zip"}}
	root := t.TempDir()
	if err := comp.prepareSQLDir(root); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(comp.backupDir, path.Join("dbm_console_dump", "dump_job")) {
		t.Fatalf("dir %s", comp.backupDir)
	}
	if comp.backupDir == path.Join(root, "dbm_console_dump") {
		t.Fatal("shared dump root")
	}
}

func TestDbConsoleDumpSqlClientArgs(t *testing.T) {
	comp := newSQLComp(t, "SELECT 1;\n", resultFormatTxt)
	var argv []string
	var defaults string
	useFakes(t, func(got []string, stdin io.Reader, outPath string) error {
		argv = append([]string{}, got...)
		defaults = strings.TrimPrefix(got[1], "--defaults-file=")
		info, err := os.Stat(defaults)
		if err != nil {
			return err
		}
		if info.Mode().Perm() != 0o600 {
			t.Fatalf("mode %o", info.Mode().Perm())
		}
		return os.WriteFile(outPath, []byte("1 row in set\n"), 0o644)
	}, nil, nil)
	forbidTxtParse(t)
	if err := comp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	if argv[0] != cst.MySQLClientPath || !strings.HasPrefix(argv[1], "--defaults-file=") || argv[2] != "--binary-mode" {
		t.Fatalf("argv %v", argv)
	}
	joined := strings.Join(argv, " ")
	if !strings.Contains(joined, "-vvv") || strings.Contains(joined, "--batch") || strings.Contains(joined, " -p") {
		t.Fatalf("argv %s", joined)
	}
	if _, err := os.Stat(defaults); !os.IsNotExist(err) {
		t.Fatal("defaults file still exists")
	}
	if !strings.Contains(joined, "--default-character-set=gbk") {
		t.Fatalf("charset argv %s", joined)
	}
}

func TestDbConsoleDumpSqlCsvRunsSetBeforeSelect(t *testing.T) {
	comp := newSQLComp(t, "SET @row_limit = 10;\nSELECT @row_limit;\n", resultFormatCSV)
	fake := &fakeExportConn{result: queryResult{Columns: []string{"@row_limit"}, Types: []string{"BIGINT"}, Rows: [][]any{{10}}}}
	useFakes(t, nil, func(dsn string) (exportConn, error) { return fake, nil }, []exportStatement{
		{QueryID: 1, Command: "set_option", QueryString: "SET @row_limit = 10;"},
		{QueryID: 2, Command: "select", QueryString: "SELECT @row_limit;"},
	})
	if err := comp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	if len(fake.execs) != 1 || fake.execs[0] != "SET @row_limit = 10;" {
		t.Fatalf("execs %v", fake.execs)
	}
	if len(fake.queries) != 1 || fake.queries[0] != "SELECT @row_limit;" {
		t.Fatalf("queries %v", fake.queries)
	}
	names := zipNames(t, filepath.Join(comp.backupDir, "dump_job.zip"))
	if strings.Join(names, ",") != "002.csv" {
		t.Fatalf("zip %v", names)
	}
}

func TestDbConsoleDumpSqlRejectsDeleteBeforeClient(t *testing.T) {
	body := "SELECT 1;\nDELETE FROM t;\n"
	comp := newSQLComp(t, body, resultFormatTxt)
	txtCalls := 0
	var stdin string
	useFakes(t, func(argv []string, in io.Reader, outPath string) error {
		txtCalls++
		stdin = readTxt(t, in)
		return os.WriteFile(outPath, []byte("rows in set\n"), 0o644)
	}, nil, nil)
	forbidTxtParse(t)
	if err := comp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	if txtCalls != 1 || stdin != body {
		t.Fatalf("txt calls %d stdin %s", txtCalls, stdin)
	}
	csvComp := newSQLComp(t, body, resultFormatCSV)
	openCalls := 0
	useFakes(t, nil, func(dsn string) (exportConn, error) {
		openCalls++
		return &fakeExportConn{}, nil
	}, []exportStatement{
		{QueryID: 1, Command: "select", QueryString: "SELECT 1;"},
		{QueryID: 2, Command: "delete", QueryString: "DELETE FROM t;"},
	})
	if err := csvComp.runSQLExport(); err == nil {
		t.Fatal("expected csv reject")
	}
	if openCalls != 0 {
		t.Fatalf("open %d", openCalls)
	}
}

func TestDbConsoleDumpSqlCsvNullAndBinary(t *testing.T) {
	comp := newSQLComp(t, "SELECT id, note, bin FROM t;\n", resultFormatCSV)
	fake := &fakeExportConn{result: queryResult{
		Columns: []string{"id", "note", "bin"},
		Types:   []string{"INT", "VARCHAR", "BLOB"},
		Rows:    [][]any{{nil, []byte("苹果"), []byte{0x00, 0xFF}}},
	}}
	useFakes(t, nil, func(dsn string) (exportConn, error) {
		if !strings.Contains(dsn, "charset=utf8mb4") {
			t.Fatalf("dsn %s", dsn)
		}
		return fake, nil
	}, []exportStatement{{QueryID: 2, Command: "select", QueryString: "SELECT id, note, bin FROM t;"}})
	if err := comp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(filepath.Join(comp.backupDir, "002.csv"))
	if err != nil {
		t.Fatal(err)
	}
	text := string(raw)
	if !strings.Contains(text, `\N`) || !strings.Contains(text, "苹果") || !strings.Contains(text, "00FF") {
		t.Fatalf("csv %s", text)
	}
	if strings.Contains(text, string([]byte{0x00})) {
		t.Fatal("raw nul byte leaked")
	}
}

func TestDbConsoleDumpSqlParseArgs(t *testing.T) {
	args := buildParseArgs(tmysqlparseBin, "a.sql", "a.json", "5.7", "tendbcluster")
	joined := strings.Join(args, " ")
	if args[0] != tmysqlparseBin || !strings.Contains(joined, "--print-query-length=1048576") {
		t.Fatalf("args %s", joined)
	}
	if !strings.Contains(joined, "--mysql-variant=mariadb") {
		t.Fatalf("variant %s", joined)
	}
	mysqlArgs := strings.Join(buildParseArgs(tmysqlparseBin, "a.sql", "a.json", "5.7", "tendbha"), " ")
	if !strings.Contains(mysqlArgs, "--mysql-variant=mysql") {
		t.Fatalf("mysql variant %s", mysqlArgs)
	}
}

func TestParseBinPathUsesEnv(t *testing.T) {
	t.Setenv("TMYSQLPARSER_BIN", "/tmp/from-env/tmysqlparse")
	if got := parseBinPath(); got != "/tmp/from-env/tmysqlparse" {
		t.Fatalf("env path %s", got)
	}
	t.Setenv("TMYSQLPARSER_BIN", "  ")
	old := tmysqlparseBin
	tmysqlparseBin = "/data/tmysqlparse"
	t.Cleanup(func() { tmysqlparseBin = old })
	if got := parseBinPath(); got != "/data/tmysqlparse" {
		t.Fatalf("default path %s", got)
	}
}

func TestMapParseVersion(t *testing.T) {
	cases := []struct {
		in   string
		want string
	}{
		{in: "MySQL-5.7", want: "5.7.20"},
		{in: "TXSQL-8.0", want: "8.0.18"},
		{in: "MySQL-8.0-Community", want: "8.0.18"},
		{in: "MySQL-8.4", want: "8.4.0"},
		{in: "5.7.20", want: "5.7.20"},
		{in: "unknown", want: ""},
	}
	for _, item := range cases {
		if got := mapParseVersion(item.in); got != item.want {
			t.Fatalf("%s -> %s, want %s", item.in, got, item.want)
		}
	}
	mapped := strings.Join(buildParseArgs(tmysqlparseBin, "a.sql", "a.json", "MySQL-5.7", "tendbha"), " ")
	if strings.Contains(mapped, "MySQL-5.7") || !strings.Contains(mapped, "--mysql-version=5.7.20") {
		t.Fatalf("mapped args %s", mapped)
	}
	bare := strings.Join(buildParseArgs(tmysqlparseBin, "a.sql", "a.json", "unknown", "tendbha"), " ")
	if strings.Contains(bare, "--mysql-version=") {
		t.Fatalf("unknown version passed: %s", bare)
	}
}

func TestEmptyParseIsFailure(t *testing.T) {
	script := filepath.Join(t.TempDir(), "tmysqlparse")
	body := "#!/bin/sh\n" +
		"out=\n" +
		"for arg in \"$@\"; do\n" +
		"  case \"$arg\" in\n" +
		"    --output-path=*) out=${arg#--output-path=} ;;\n" +
		"  esac\n" +
		"done\n" +
		": > \"$out\"\n" +
		"echo \"invalid character: 'M'\"\n" +
		"echo \"ERROR bad version\"\n" +
		"exit 0\n"
	if err := os.WriteFile(script, []byte(body), 0o700); err != nil {
		t.Fatal(err)
	}
	t.Setenv("TMYSQLPARSER_BIN", "")
	oldBin := tmysqlparseBin
	tmysqlparseBin = script
	t.Cleanup(func() { tmysqlparseBin = oldBin })
	filePath, unusedDigest := writeSQL(t, "SELECT 1;\n")
	if unusedDigest == "" {
		t.Fatal("digest")
	}
	lines, err := defaultParseExportStatements(filePath, "unknown", "tendbha")
	if err == nil {
		t.Fatalf("empty parse succeeded with %d lines", len(lines))
	}
	comp := newSQLComp(t, "SELECT 1;\n", resultFormatCSV)
	useFakes(t, nil, nil, nil)
	parseExportStatements = defaultParseExportStatements
	comp.Params.MysqlVersion = "unknown"
	if err = comp.runSQLExport(); err == nil {
		t.Fatal("export succeeded on empty parse")
	}
	if _, statErr := os.Stat(filepath.Join(comp.backupDir, queryResultFileName)); !os.IsNotExist(statErr) {
		t.Fatal("query_result.txt remains")
	}
}

func TestExecRejectsSleepAndDerivedSystemDB(t *testing.T) {
	rejects := []exportStatement{
		{QueryID: 1, Command: "select", QueryString: "SELECT SLEEP(1);"},
		{QueryID: 1, Command: "select", QueryString: "SELECT BENCHMARK(1, 1);"},
		{QueryID: 1, Command: "select", QueryString: "SELECT LOAD_FILE('/tmp/a');"},
		{QueryID: 1, Command: "select", QueryString: "SELECT 1 INTO OUTFILE '/tmp/a';"},
		{QueryID: 1, Command: "change_db", DbName: "mysql", QueryString: "USE mysql;"},
		{
			QueryID: 1, Command: "select", QueryString: "SELECT * FROM dt JOIN app.u",
			QueryDigestText: "SELECT * FROM ( SELECT `id` FROM `mysql` . `user` ) `dt` JOIN `app` . `u` ",
			TableReferences: []exportTableRef{{DbName: "app", TableName: "u"}},
		},
		{
			QueryID: 1, Command: "select", QueryString: "SELECT (SELECT MAX(id) FROM mysql.user) FROM app.u",
			QueryDigestText: "SELECT ( SELECT MAX(`id`) FROM `mysql` . `user` ) FROM `app` . `u` ",
			TableReferences: []exportTableRef{{DbName: "app", TableName: "u"}},
		},
		{QueryID: 1, Command: "change_db", DbName: "app", QueryString: "USE app;"},
	}
	for _, line := range rejects {
		comp := newSQLComp(t, line.QueryString+"\n", resultFormatCSV)
		calls := 0
		useFakes(t, func(argv []string, in io.Reader, outPath string) error {
			calls++
			return os.WriteFile(outPath, []byte("rows in set\n"), 0o644)
		}, func(dsn string) (exportConn, error) {
			calls++
			return &fakeExportConn{}, nil
		}, []exportStatement{line})
		if err := comp.runSQLExport(); err == nil {
			t.Fatalf("accepted %s", line.QueryString)
		}
		if calls != 0 {
			t.Fatalf("started client for %s", line.QueryString)
		}
	}
	comp := newSQLComp(t, "USE app;\nSELECT 1;\n", resultFormatTxt)
	useFakes(t, func(argv []string, in io.Reader, outPath string) error {
		return os.WriteFile(outPath, []byte("1 row in set\n"), 0o644)
	}, nil, nil)
	forbidTxtParse(t)
	if err := comp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	unionComp := newSQLComp(t, "SELECT 1 FROM app.t UNION SELECT 2 FROM app.u;\n", resultFormatTxt)
	useFakes(t, func(argv []string, in io.Reader, outPath string) error {
		return os.WriteFile(outPath, []byte("2 rows in set\n"), 0o644)
	}, nil, nil)
	forbidTxtParse(t)
	if err := unionComp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
}

func TestCsvWriteFailureDeletesFile(t *testing.T) {
	comp := newSQLComp(t, "SELECT 1;\n", resultFormatCSV)
	fake := &fakeExportConn{writeErr: os.ErrInvalid, result: queryResult{Columns: []string{"id"}, Types: []string{"INT"}}}
	useFakes(t, nil, func(dsn string) (exportConn, error) { return fake, nil }, []exportStatement{
		{QueryID: 2, Command: "select", QueryString: "SELECT 1;"},
	})
	if err := comp.runSQLExport(); err == nil {
		t.Fatal("expected write error")
	}
	if _, err := os.Stat(filepath.Join(comp.backupDir, "002.csv")); !os.IsNotExist(err) {
		t.Fatal("partial csv remains")
	}
}

func TestCsvDsnUsesUtf8mb4(t *testing.T) {
	comp := newSQLComp(t, "SELECT 1;\n", resultFormatCSV)
	comp.charset = "gbk"
	var dsn string
	useFakes(t, nil, func(got string) (exportConn, error) {
		dsn = got
		return &fakeExportConn{result: queryResult{Columns: []string{"id"}, Types: []string{"INT"}, Rows: [][]any{{1}}}}, nil
	}, []exportStatement{{QueryID: 1, Command: "select", QueryString: "SELECT 1;"}})
	if err := comp.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(dsn, "charset=utf8mb4") || strings.Contains(dsn, "charset=gbk") {
		t.Fatalf("dsn %s", dsn)
	}
	txt := newSQLComp(t, "SELECT 1;\n", resultFormatTxt)
	txt.charset = "gbk"
	var argv []string
	useFakes(t, func(got []string, in io.Reader, outPath string) error {
		argv = got
		return os.WriteFile(outPath, []byte("1 row in set\n"), 0o644)
	}, nil, nil)
	forbidTxtParse(t)
	if err := txt.runSQLExport(); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(strings.Join(argv, " "), "--default-character-set=gbk") {
		t.Fatalf("txt argv %v", argv)
	}
}

func TestCsvStreamHundredThousandInts(t *testing.T) {
	filePath := filepath.Join(t.TempDir(), "rows.csv")
	n := 0
	var peak uint64
	var before uint64
	runtime.GC()
	var stats runtime.MemStats
	runtime.ReadMemStats(&stats)
	before = stats.HeapAlloc
	err := writeCSVStream(filePath, []string{"id"}, []string{"INT"}, func() ([]any, error) {
		if n >= 100000 {
			return nil, io.EOF
		}
		n++
		if n%10000 == 0 {
			runtime.ReadMemStats(&stats)
			if stats.HeapAlloc > peak {
				peak = stats.HeapAlloc
			}
		}
		return []any{n}, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if peak > before && peak-before > 64<<20 {
		t.Fatalf("heap grew %d", peak-before)
	}
}
