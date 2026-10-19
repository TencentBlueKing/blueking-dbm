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
	"bufio"
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/csv"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path"
	"regexp"
	"strings"

	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

const (
	exportModeSQL       = "sql"
	resultFormatTxt     = "txt"
	resultFormatCSV     = "csv"
	printQueryLength    = 1048576
	queryResultFileName = "query_result.txt"
)

var tmysqlparseBin = "/data/tmysqlparse"

func parseBinPath() string {
	if bin := strings.TrimSpace(os.Getenv("TMYSQLPARSER_BIN")); bin != "" {
		return bin
	}
	if bin := strings.TrimSpace(tmysqlparseBin); bin != "" {
		return bin
	}
	return "/data/tmysqlparse"
}

type exportTableRef struct {
	DbName    string `json:"db_name"`
	TableName string `json:"table_name"`
}

type exportStatement struct {
	QueryID         int              `json:"query_id"`
	Command         string           `json:"command"`
	DbName          string           `json:"db_name"`
	QueryString     string           `json:"query_string"`
	QueryDigestText string           `json:"query_digest_text"`
	ErrorCode       int              `json:"error_code"`
	ErrorMsg        string           `json:"error_msg"`
	TableReferences []exportTableRef `json:"table_references"`
}

type queryResult struct {
	Columns []string
	Types   []string
	Rows    [][]any
}

type exportConn interface {
	Exec(ctx context.Context, query string) error
	WriteQueryCSV(ctx context.Context, query, filePath string) error
	Close() error
}

var (
	reSleepOrBenchmark = regexp.MustCompile(`(?i)\b(SLEEP|BENCHMARK)\s*\(`)
	reIntoOutfile      = regexp.MustCompile(`(?i)\bINTO\s+(OUTFILE|DUMPFILE)\b`)
	reLoadFile         = regexp.MustCompile(`(?i)\bLOAD_FILE\s*\(`)
	reDigestQualified  = regexp.MustCompile("`([^`]+)`\\s*\\.\\s*`[^`]+`")
	exportSystemDBs    = map[string]struct{}{
		"mysql": {}, "test": {}, "db_infobase": {}, "information_schema": {},
		"performance_schema": {}, "sys": {}, "infodba_schema": {},
	}
)

type txtClientFunc func(argv []string, stdin io.Reader, outPath string) error
type parseFunc func(sqlFile, version, clusterType string) ([]exportStatement, error)
type openConnFunc func(dsn string) (exportConn, error)

var (
	runTxtClient          txtClientFunc = defaultRunTxtClient
	parseExportStatements parseFunc     = defaultParseExportStatements
	openExportConn        openConnFunc  = defaultOpenExportConn
)

func (c *DbConsoleDumpComp) isSQLExport() bool {
	return c.Params.ExportMode == exportModeSQL
}

func (c *DbConsoleDumpComp) initSQLExport(conn *native.DbWorker, rootDir string) error {
	c.charset = strings.TrimSpace(c.Params.CharSet)
	if strings.EqualFold(c.charset, "default") || c.charset == "" {
		serverCharset, err := conn.ShowServerCharset()
		if err != nil {
			return err
		}
		c.charset = serverCharset
	}
	return c.prepareSQLDir(rootDir)
}

func (c *DbConsoleDumpComp) prepareSQLDir(rootDir string) error {
	stem := strings.TrimSuffix(c.Params.ZipFileName, ".zip")
	if stem == "" || strings.Contains(stem, "..") || strings.ContainsAny(stem, `/\`) {
		return fmt.Errorf("invalid zip file name")
	}
	c.backupDir = path.Join(rootDir, "dbm_console_dump", stem)
	return os.MkdirAll(c.backupDir, 0o750)
}

func (c *DbConsoleDumpComp) runSQLExport() error {
	if err := matchSHA256(c.Params.SqlLocalPath, c.Params.SqlSha256); err != nil {
		return err
	}
	format := c.Params.ResultFormat
	if format == "" {
		format = resultFormatTxt
	}
	var names []string
	var err error
	switch format {
	case resultFormatTxt:
		names, err = c.exportTxt()
	case resultFormatCSV:
		names, err = c.exportCSVChecked()
	default:
		err = fmt.Errorf("unsupported result format %s", format)
	}
	if err != nil {
		c.removeNames(names)
		return err
	}
	if err = zipFiles(c.backupDir, names, c.Params.ZipFileName); err != nil {
		c.removeNames(names)
		return err
	}
	if c.sqlUpload != nil {
		return c.sqlUpload()
	}
	return nil
}

func (c *DbConsoleDumpComp) exportCSVChecked() ([]string, error) {
	lines, err := parseExportStatements(c.Params.SqlLocalPath, c.Params.MysqlVersion, c.Params.ClusterType)
	if err != nil {
		return nil, err
	}
	if err = rejectBadCommands(lines); err != nil {
		return nil, err
	}
	if err = rejectExecRisks(lines); err != nil {
		return nil, err
	}
	selectCount := 0
	for _, line := range lines {
		if strings.EqualFold(line.Command, "select") {
			selectCount++
		}
	}
	if selectCount == 0 {
		return nil, fmt.Errorf("no select")
	}
	return c.exportCSV(lines)
}

func (c *DbConsoleDumpComp) exportTxt() ([]string, error) {
	defaultsPath := path.Join(c.backupDir, "client.cnf")
	if err := writeClientDefaults(defaultsPath, c.clientAccount()); err != nil {
		return nil, err
	}
	defer os.Remove(defaultsPath)
	sqlFile, err := os.Open(c.Params.SqlLocalPath)
	if err != nil {
		return nil, err
	}
	defer sqlFile.Close()
	outPath := path.Join(c.backupDir, queryResultFileName)
	argv := []string{
		cst.MySQLClientPath,
		"--defaults-file=" + defaultsPath,
		"--binary-mode",
		"-vvv",
		"--default-character-set=" + c.charset,
	}
	if err = runTxtClient(argv, sqlFile, outPath); err != nil {
		return []string{queryResultFileName}, err
	}
	return []string{queryResultFileName}, nil
}

func (c *DbConsoleDumpComp) exportCSV(lines []exportStatement) ([]string, error) {
	conn, err := openExportConn(c.exportDSN())
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	var names []string
	ctx := context.Background()
	for _, line := range lines {
		if strings.EqualFold(line.Command, "change_db") || strings.EqualFold(line.Command, "set_option") {
			if err = conn.Exec(ctx, line.QueryString); err != nil {
				return names, err
			}
			continue
		}
		name := fmt.Sprintf("%03d.csv", line.QueryID)
		names = append(names, name)
		if err = conn.WriteQueryCSV(ctx, line.QueryString, path.Join(c.backupDir, name)); err != nil {
			return names, err
		}
	}
	return names, nil
}

func (c *DbConsoleDumpComp) exportDSN() string {
	account := c.clientAccount()
	return fmt.Sprintf("%s:%s@tcp(%s:%d)/?charset=utf8mb4&multiStatements=false",
		account.user, account.password, account.host, account.port)
}

type clientAccount struct {
	user     string
	password string
	host     string
	port     int
}

func (c *DbConsoleDumpComp) clientAccount() clientAccount {
	account := clientAccount{host: c.Params.Host, port: c.Params.Port}
	if c.GeneralParam != nil {
		account.user = c.GeneralParam.RuntimeAccountParam.AdminUser
		account.password = c.GeneralParam.RuntimeAccountParam.AdminPwd
	}
	return account
}

func (c *DbConsoleDumpComp) removeNames(names []string) {
	for _, name := range names {
		_ = os.Remove(path.Join(c.backupDir, name))
	}
	if c.Params.ZipFileName != "" {
		_ = os.Remove(path.Join(c.backupDir, c.Params.ZipFileName))
	}
}

func writeClientDefaults(filePath string, account clientAccount) error {
	body := fmt.Sprintf("[client]\nuser=%s\npassword=%s\nhost=%s\nport=%d\n",
		account.user, account.password, account.host, account.port)
	return os.WriteFile(filePath, []byte(body), 0o600)
}

func rejectBadCommands(lines []exportStatement) error {
	for _, line := range lines {
		if line.ErrorCode != 0 {
			return fmt.Errorf("statement %d syntax error: %s", line.QueryID, line.ErrorMsg)
		}
		if len(line.QueryString) >= printQueryLength {
			return fmt.Errorf("statement %d truncated", line.QueryID)
		}
		command := strings.ToLower(line.Command)
		if command != "select" && command != "change_db" && command != "set_option" {
			return fmt.Errorf("statement %d command %s", line.QueryID, line.Command)
		}
	}
	return nil
}

func mapParseVersion(version string) string {
	switch {
	case strings.Contains(version, "5.5"):
		return "5.5.24"
	case strings.Contains(version, "5.6"):
		return "5.6.24"
	case strings.Contains(version, "5.7"):
		return "5.7.20"
	case strings.Contains(version, "8.0"):
		return "8.0.18"
	case strings.Contains(version, "8.4"):
		return "8.4.0"
	default:
		return ""
	}
}

func rejectExecRisks(lines []exportStatement) error {
	for _, line := range lines {
		if err := rejectInjectText(line); err != nil {
			return err
		}
		if err := rejectSystemDB(line); err != nil {
			return err
		}
	}
	return nil
}

func rejectInjectText(line exportStatement) error {
	text := line.QueryString
	if reSleepOrBenchmark.MatchString(text) || reLoadFile.MatchString(text) || reIntoOutfile.MatchString(text) {
		return fmt.Errorf("statement %d dangerous sql", line.QueryID)
	}
	return nil
}

func rejectSystemDB(line exportStatement) error {
	if strings.EqualFold(line.Command, "change_db") && isExportSystemDB(line.DbName) {
		return fmt.Errorf("statement %d system db %s", line.QueryID, line.DbName)
	}
	for _, ref := range line.TableReferences {
		if isExportSystemDB(ref.DbName) {
			return fmt.Errorf("statement %d system db %s", line.QueryID, ref.DbName)
		}
	}
	for _, match := range reDigestQualified.FindAllStringSubmatch(line.QueryDigestText, -1) {
		if isExportSystemDB(match[1]) {
			return fmt.Errorf("statement %d system db %s", line.QueryID, match[1])
		}
	}
	return nil
}

func isExportSystemDB(name string) bool {
	_, ok := exportSystemDBs[strings.ToLower(strings.TrimSpace(name))]
	return ok
}

func matchSHA256(filePath, expect string) error {
	if strings.TrimSpace(expect) == "" {
		return fmt.Errorf("sql sha256 is empty")
	}
	raw, err := os.ReadFile(filePath)
	if err != nil {
		return err
	}
	sum := sha256.Sum256(raw)
	got := hex.EncodeToString(sum[:])
	if !strings.EqualFold(got, strings.TrimSpace(expect)) {
		return fmt.Errorf("sql sha256 mismatch")
	}
	return nil
}

func defaultRunTxtClient(argv []string, stdin io.Reader, outPath string) error {
	out, err := os.Create(outPath)
	if err != nil {
		return err
	}
	defer out.Close()
	cmd := exec.Command(argv[0], argv[1:]...)
	cmd.Stdin = stdin
	cmd.Stdout = out
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func buildParseArgs(bin, sqlFile, outFile, version, clusterType string) []string {
	args := []string{
		bin,
		"--sql-file=" + sqlFile,
		"--output-path=" + outFile,
		"--print-query-mode=2",
		"--output-format=JSON_LINE_PER_OBJECT",
		"--sql-mode=",
		"--print-query-length=1048576",
	}
	if mapped := mapParseVersion(version); mapped != "" {
		args = append(args, "--mysql-version="+mapped)
	}
	variant := "mysql"
	if clusterType == "tendbcluster" || clusterType == "spider" {
		variant = "mariadb"
	}
	args = append(args, "--mysql-variant="+variant)
	return args
}

func defaultParseExportStatements(sqlFile, version, clusterType string) ([]exportStatement, error) {
	outFile := sqlFile + ".parse.json"
	defer os.Remove(outFile)
	args := buildParseArgs(parseBinPath(), sqlFile, outFile, version, clusterType)
	cmd := exec.Command(args[0], args[1:]...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("tmysqlparse failed: %w: %s", err, string(output))
	}
	if strings.Contains(string(output), "ERROR") || strings.Contains(string(output), "invalid character") {
		return nil, fmt.Errorf("tmysqlparse error: %s", string(output))
	}
	info, statErr := os.Stat(outFile)
	if statErr != nil || info.Size() == 0 {
		return nil, fmt.Errorf("tmysqlparse empty output")
	}
	return readExportStatements(outFile)
}

func readExportStatements(outFile string) ([]exportStatement, error) {
	f, err := os.Open(outFile)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var lines []exportStatement
	reader := bufio.NewReader(f)
	for {
		raw, errx := reader.ReadBytes('\n')
		if len(raw) > 0 && strings.TrimSpace(string(raw)) != "" {
			var line exportStatement
			if uerr := json.Unmarshal(raw, &line); uerr != nil {
				return nil, uerr
			}
			if line.Command != "" || line.ErrorCode != 0 {
				lines = append(lines, line)
			}
		}
		if errx == io.EOF {
			break
		}
		if errx != nil {
			return nil, errx
		}
	}
	return lines, nil
}

func defaultOpenExportConn(dsn string) (exportConn, error) {
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return nil, err
	}
	ctx := context.Background()
	conn, err := db.Conn(ctx)
	if err != nil {
		_ = db.Close()
		return nil, err
	}
	return &sqlExportConn{db: db, conn: conn}, nil
}

type sqlExportConn struct {
	db   *sql.DB
	conn *sql.Conn
}

func (s *sqlExportConn) Exec(ctx context.Context, query string) error {
	_, err := s.conn.ExecContext(ctx, query)
	return err
}

func (s *sqlExportConn) WriteQueryCSV(ctx context.Context, query, filePath string) error {
	rows, err := s.conn.QueryContext(ctx, query)
	if err != nil {
		return err
	}
	defer rows.Close()
	cols, err := rows.Columns()
	if err != nil {
		return err
	}
	colTypes, err := rows.ColumnTypes()
	if err != nil {
		return err
	}
	types := make([]string, len(colTypes))
	for i, colType := range colTypes {
		types[i] = colType.DatabaseTypeName()
	}
	return writeCSVStream(filePath, cols, types, func() ([]any, error) {
		if !rows.Next() {
			if err = rows.Err(); err != nil {
				return nil, err
			}
			return nil, io.EOF
		}
		vals := make([]any, len(cols))
		ptrs := make([]any, len(cols))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		if err = rows.Scan(ptrs...); err != nil {
			return nil, err
		}
		return vals, nil
	})
}

func (s *sqlExportConn) Close() error {
	cerr := s.conn.Close()
	derr := s.db.Close()
	if cerr != nil {
		return cerr
	}
	return derr
}

func writeCSV(filePath string, res queryResult) error {
	index := 0
	return writeCSVStream(filePath, res.Columns, res.Types, func() ([]any, error) {
		if index >= len(res.Rows) {
			return nil, io.EOF
		}
		row := res.Rows[index]
		index++
		return row, nil
	})
}

func writeCSVStream(filePath string, cols, types []string, next func() ([]any, error)) error {
	f, err := os.Create(filePath)
	if err != nil {
		return err
	}
	defer f.Close()
	if _, err = f.Write([]byte{0xEF, 0xBB, 0xBF}); err != nil {
		return err
	}
	writer := csv.NewWriter(f)
	if err = writer.Write(cols); err != nil {
		return err
	}
	for {
		row, nextErr := next()
		if nextErr == io.EOF {
			break
		}
		if nextErr != nil {
			return nextErr
		}
		record := make([]string, len(cols))
		for i := range cols {
			var val any
			if i < len(row) {
				val = row[i]
			}
			typ := ""
			if i < len(types) {
				typ = types[i]
			}
			record[i] = formatCSVCell(val, typ)
		}
		if err = writer.Write(record); err != nil {
			return err
		}
	}
	writer.Flush()
	return writer.Error()
}

func formatCSVCell(val any, typ string) string {
	if val == nil {
		return `\N`
	}
	if isBinaryColumn(typ) {
		return strings.ToUpper(hex.EncodeToString(asBytes(val)))
	}
	switch typed := val.(type) {
	case []byte:
		return string(typed)
	case string:
		return typed
	default:
		return fmt.Sprint(typed)
	}
}

func isBinaryColumn(typ string) bool {
	switch strings.ToUpper(typ) {
	case "BLOB", "TINYBLOB", "MEDIUMBLOB", "LONGBLOB", "BINARY", "VARBINARY", "BIT":
		return true
	default:
		return false
	}
}

func asBytes(val any) []byte {
	switch typed := val.(type) {
	case []byte:
		return typed
	case string:
		return []byte(typed)
	default:
		return []byte(fmt.Sprint(typed))
	}
}
