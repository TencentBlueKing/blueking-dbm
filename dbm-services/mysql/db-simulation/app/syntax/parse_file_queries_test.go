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
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"dbm-services/mysql/db-simulation/app"
)

func parseBin(t *testing.T) string {
	t.Helper()
	for _, bin := range []string{"/data/tmysqlparse", "/tmysqlparse"} {
		if _, err := os.Stat(bin); err == nil {
			return bin
		}
	}
	t.Skip("tmysqlparse binary not found")
	return ""
}

func parseQueries(t *testing.T, sql, clusterType string) []ParseFileQuery {
	t.Helper()
	dir := t.TempDir()
	name := "q.sql"
	if err := os.WriteFile(filepath.Join(dir, name), []byte(sql), 0600); err != nil {
		t.Fatal(err)
	}
	tf := &TmysqlParseFile{
		TmysqlParse: TmysqlParse{
			TmysqlParseBinPath: parseBin(t),
			BaseWorkdir:        dir,
		},
		IsLocalFile: true,
		Param: CheckSQLFileParam{
			FileNames:   []string{name},
			ClusterType: clusterType,
		},
	}
	lines, err := tf.DoParseFileQueries("5.7")
	if err != nil {
		t.Fatal(err)
	}
	return lines
}

func TestGetCommandOmitsPrintLengthByDefault(t *testing.T) {
	tf := &TmysqlParseFile{
		TmysqlParse: TmysqlParse{TmysqlParseBinPath: "/data/tmysqlparse"},
	}
	tf.tmpWorkdir = t.TempDir()
	cmd := tf.getCommand("a.sql", "5.7", "")
	if strings.Contains(cmd, "print-query-length") {
		t.Fatalf("default command must not set print length: %s", cmd)
	}
	if !strings.Contains(cmd, "--mysql-variant=mysql") {
		t.Fatalf("mysql variant missing: %s", cmd)
	}
	cmd = tf.getCommand("a.sql", "5.7", app.TendbCluster)
	if !strings.Contains(cmd, "--mysql-variant=mariadb") {
		t.Fatalf("mariadb variant missing: %s", cmd)
	}
}

func TestParseFileQueriesUseFillsTable(t *testing.T) {
	lines := parseQueries(t, "USE app;\nSELECT id FROM t;\n", "")
	if len(lines) != 2 {
		t.Fatalf("lines=%d", len(lines))
	}
	if lines[0].Command != "change_db" || lines[0].DbName != "app" {
		t.Fatalf("use line: %+v", lines[0])
	}
	if lines[1].Command != "select" || len(lines[1].TableReferences) != 1 {
		t.Fatalf("select line: %+v", lines[1])
	}
	ref := lines[1].TableReferences[0]
	if ref.DbName != "app" || ref.TableName != "t" {
		t.Fatalf("ref: %+v", ref)
	}
	for _, line := range lines {
		if line.Command == "" {
			t.Fatalf("version trailer leaked: %+v", line)
		}
	}
}

func TestParseFileQueriesInsertAndSchemaCase(t *testing.T) {
	lines := parseQueries(t, "INSERT INTO app.t VALUES (1);\nSELECT * FROM INFORMATION_SCHEMA.TABLES;\n", "")
	if len(lines) != 2 {
		t.Fatalf("lines=%d %+v", len(lines), lines)
	}
	if lines[0].Command != "insert" || lines[0].QueryID == 0 {
		t.Fatalf("insert: %+v", lines[0])
	}
	if len(lines[1].TableReferences) != 1 || lines[1].TableReferences[0].DbName != "INFORMATION_SCHEMA" {
		t.Fatalf("schema case: %+v", lines[1].TableReferences)
	}
}

func TestParseFileQueriesDerivedAndMissingUse(t *testing.T) {
	derived := parseQueries(t, "SELECT * FROM (SELECT * FROM mysql.user) AS dt;\n", "")
	if len(derived) != 1 {
		t.Fatalf("derived lines=%d", len(derived))
	}
	if len(derived[0].TableReferences) != 0 {
		t.Fatalf("derived refs: %+v", derived[0].TableReferences)
	}
	digest := derived[0].QueryDigestText
	if !strings.Contains(digest, "mysql") || !strings.Contains(digest, "user") {
		t.Fatalf("digest: %s", digest)
	}

	missing := parseQueries(t, "SELECT id FROM t;\n", "")
	if len(missing) != 1 || len(missing[0].TableReferences) != 1 {
		t.Fatalf("missing use: %+v", missing)
	}
	if missing[0].TableReferences[0].DbName != "" || missing[0].DbName != "" {
		t.Fatalf("db should be empty: %+v", missing[0])
	}
}

func TestParseFileQueriesManySelectsAreNotMultiInject(t *testing.T) {
	var b strings.Builder
	for i := 0; i < 20; i++ {
		b.WriteString("SELECT 1;\n")
	}
	lines := parseQueries(t, b.String(), "")
	if len(lines) != 20 {
		t.Fatalf("lines=%d", len(lines))
	}
	for _, line := range lines {
		if line.IsInject || strings.Contains(line.Reason, "多语句") {
			t.Fatalf("false inject: %+v", line)
		}
	}
	one := parseQueries(t, "SELECT 'a;b';\n", "")
	if len(one) != 1 || one[0].Command != "select" || one[0].IsInject {
		t.Fatalf("quoted semicolon: %+v", one)
	}
}

func TestParseFileQueriesCommentAndInject(t *testing.T) {
	comments := parseQueries(t, "-- only a comment\n", "")
	if len(comments) != 1 || comments[0].ErrorCode == 0 {
		t.Fatalf("comment-only: %+v", comments)
	}

	lines := parseQueries(t, "SELECT SLEEP(1);\nSELECT 1;\nSELECT 1 UNION SELECT 2;\nSELECT 1 WHERE 1=1 OR 1=1;\n", "")
	if len(lines) != 4 {
		t.Fatalf("lines=%d %+v", len(lines), lines)
	}
	if !lines[0].IsInject || !strings.Contains(lines[0].Reason, "SLEEP") {
		t.Fatalf("sleep: %+v", lines[0])
	}
	if lines[1].IsInject {
		t.Fatalf("clean select: %+v", lines[1])
	}
	if lines[2].IsInject || strings.Contains(lines[2].Reason, "UNION") {
		t.Fatalf("union should be kept: %+v", lines[2])
	}
	if lines[3].IsInject || strings.Contains(lines[3].Reason, "恒真") {
		t.Fatalf("tautology should be kept: %+v", lines[3])
	}
}

func TestParseFileQueriesKeepsLongQueryString(t *testing.T) {
	sql := "SELECT '" + strings.Repeat("a", 200) + "';\n"
	lines := parseQueries(t, sql, "")
	if len(lines) != 1 {
		t.Fatalf("lines=%d", len(lines))
	}
	if len(lines[0].QueryString) <= 128 {
		t.Fatalf("query_string still truncated: %d", len(lines[0].QueryString))
	}
}

func TestParseFileQueriesTruncatesAtLimit(t *testing.T) {
	sql := "SELECT '" + strings.Repeat("a", printQueryLengthLimit) + "';\n"
	lines := parseQueries(t, sql, "")
	if len(lines) != 1 {
		t.Fatalf("lines=%d", len(lines))
	}
	if lines[0].ErrorCode != queryTruncatedCode || lines[0].QueryString != "" {
		t.Fatalf("truncate: code=%d qlen=%d msg=%s", lines[0].ErrorCode, len(lines[0].QueryString), lines[0].ErrorMsg)
	}
	if lines[0].IsInject {
		t.Fatalf("truncated body must not be inject-matched")
	}
}

func TestParseFileQueriesContentSHA256(t *testing.T) {
	sql := "SELECT 1;\n"
	dir := t.TempDir()
	name := "q.sql"
	if err := os.WriteFile(filepath.Join(dir, name), []byte(sql), 0600); err != nil {
		t.Fatal(err)
	}
	tf := &TmysqlParseFile{
		TmysqlParse: TmysqlParse{
			TmysqlParseBinPath: parseBin(t),
			BaseWorkdir:        dir,
		},
		IsLocalFile: true,
		Param:       CheckSQLFileParam{FileNames: []string{name}},
	}
	if _, err := tf.DoParseFileQueries("5.7"); err != nil {
		t.Fatal(err)
	}
	got, err := tf.ContentSHA256()
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256([]byte(sql))
	want := hex.EncodeToString(sum[:])
	if got != want {
		t.Fatalf("sha %s want %s", got, want)
	}
}
