/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package handler

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"testing"
)

const testXlsxFileName = "mapleleaf(591)mysql_cluster_20261104101251.xlsx"

var testDBMHeadersZh = []string{
	"集群 ID", "db类型", "集群名称", "集群别名", "集群类型", "主域名", "从域名", "clb", "Master", "Slave", "Proxy",
	"标签", "状态", "容量使用率", "模块", "版本", "容灾要求", "地域园区", "规格", "管控区域", "创建人", "部署时间", "时区",
}

var testDBMHeadersEn = []string{
	"Cluster ID", "DB type", "Cluster name", "Cluster alias", "Cluster type", "Primary domain name",
	"Slave domain name", "clb", "Master", "Slave", "Proxy", "Tag", "state", "Capacity usage", "Module",
	"Version", "Disaster tolerance", "Region", "Specification", "control area", "Creator", "Deploy time",
	"Time zone",
}

type testXlsxCell struct {
	col   string
	kind  string
	value string
}

type testXlsxRow struct {
	num    int
	hidden string
	cells  []testXlsxCell
}

type testXlsxSheet struct {
	name  string
	state string
}

type testXlsxBook struct {
	sheets      []testXlsxSheet
	rows        []testXlsxRow
	sheetPrefix string
}

type testCluster struct {
	id          string
	domain      string
	cloud       string
	clusterType string
	status      string
}

func sCell(value string) testXlsxCell {
	return testXlsxCell{kind: xlsxCellTypeShared, value: value}
}

func nCell(value string) testXlsxCell {
	return testXlsxCell{kind: xlsxCellTypeNumber, value: value}
}

func testColLetters(index int) string {
	letters := ""
	for index >= 0 {
		letters = string(rune('A'+index%26)) + letters
		index = index/26 - 1
	}

	return letters
}

func testHeaderRow(headers []string) testXlsxRow {
	cells := make([]testXlsxCell, 0, len(headers))
	for i, header := range headers {
		cell := sCell(header)
		cell.col = testColLetters(i)
		cells = append(cells, cell)
	}

	return testXlsxRow{cells: cells}
}

func testClusterRow(headers []string, cluster testCluster) testXlsxRow {
	cells := make([]testXlsxCell, 0, len(headers))
	for i, rawHeader := range headers {
		header := strings.TrimSpace(rawHeader)
		var cell testXlsxCell
		switch {
		case matchXlsxHeader(header, xlsxColumnSpecs[xlsxColClusterID].aliases):
			cell = nCell(cluster.id)
		case matchXlsxHeader(header, xlsxColumnSpecs[xlsxColDomain].aliases):
			cell = sCell(cluster.domain)
		case matchXlsxHeader(header, xlsxColumnSpecs[xlsxColBkCloudID].aliases):
			cell = nCell(cluster.cloud)
		case matchXlsxHeader(header, xlsxColumnSpecs[xlsxColClusterType].aliases):
			cell = sCell(cluster.clusterType)
		case matchXlsxHeader(header, xlsxColumnSpecs[xlsxColStatus].aliases):
			cell = sCell(cluster.status)
		case header == "Master":
			cell = sCell("127.0.0.1#20000")
		case header == "Slave" || header == "Proxy" || header == "clb":
			continue
		default:
			cell = sCell("filler")
		}
		if cell.value == "" {
			continue
		}
		cell.col = testColLetters(i)
		cells = append(cells, cell)
	}

	return testXlsxRow{cells: cells}
}

func testRowsFromClusters(headers []string, clusters []testCluster) []testXlsxRow {
	rows := []testXlsxRow{testHeaderRow(headers)}
	for _, cluster := range clusters {
		rows = append(rows, testClusterRow(headers, cluster))
	}

	return rows
}

func testEscapeXML(t *testing.T, value string) string {
	t.Helper()

	var buf bytes.Buffer
	if err := xml.EscapeText(&buf, []byte(value)); err != nil {
		t.Fatalf("escape xml failed: %s", err)
	}

	return buf.String()
}

func buildTestSheetXML(t *testing.T, book testXlsxBook) (string, string) {
	t.Helper()

	var sheet, shared strings.Builder
	sharedCount := 0
	sheet.WriteString(`<?xml version="1.0" encoding="UTF-8"?>`)
	sheet.WriteString(`<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">`)
	sheet.WriteString(book.sheetPrefix)
	sheet.WriteString(`<sheetData>`)
	for i, row := range book.rows {
		num := row.num
		if num == 0 {
			num = i + 1
		}
		hidden := ""
		if row.hidden != "" {
			hidden = fmt.Sprintf(` hidden="%s"`, row.hidden)
		}
		fmt.Fprintf(&sheet, `<row r="%d"%s>`, num, hidden)
		for _, cell := range row.cells {
			ref := ""
			if cell.col != "" {
				ref = fmt.Sprintf(` r="%s%d"`, cell.col, num)
			}
			switch cell.kind {
			case xlsxCellTypeShared:
				fmt.Fprintf(&shared, `<si><t>%s</t></si>`, testEscapeXML(t, cell.value))
				fmt.Fprintf(&sheet, `<c%s t="s"><v>%d</v></c>`, ref, sharedCount)
				sharedCount++
			case "sraw":
				fmt.Fprintf(&shared, `<si>%s</si>`, cell.value)
				fmt.Fprintf(&sheet, `<c%s t="s"><v>%d</v></c>`, ref, sharedCount)
				sharedCount++
			case xlsxCellTypeInline:
				fmt.Fprintf(&sheet, `<c%s t="inlineStr"><is><t>%s</t></is></c>`, ref, testEscapeXML(t, cell.value))
			case xlsxCellTypeNumber:
				fmt.Fprintf(&sheet, `<c%s><v>%s</v></c>`, ref, testEscapeXML(t, cell.value))
			default:
				fmt.Fprintf(&sheet, `<c%s t="%s"><v>%s</v></c>`, ref, cell.kind, testEscapeXML(t, cell.value))
			}
		}
		sheet.WriteString(`</row>`)
	}
	sheet.WriteString(`</sheetData></worksheet>`)

	sst := `<?xml version="1.0" encoding="UTF-8"?>` +
		`<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` + shared.String() + `</sst>`

	return sheet.String(), sst
}

func writeTestXlsx(t *testing.T, filePath string, book testXlsxBook) {
	t.Helper()

	sheets := book.sheets
	if len(sheets) == 0 {
		sheets = []testXlsxSheet{{name: "Sheet"}}
	}

	sheetXML, sstXML := buildTestSheetXML(t, book)
	var workbook, rels strings.Builder
	workbook.WriteString(`<?xml version="1.0" encoding="UTF-8"?><workbook ` +
		`xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ` +
		`xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>`)
	rels.WriteString(`<?xml version="1.0" encoding="UTF-8"?>` +
		`<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">`)
	entries := map[string]string{xlsxPathSharedStrings: sstXML}
	for i, sheet := range sheets {
		state := ""
		if sheet.state != "" {
			state = fmt.Sprintf(` state="%s"`, sheet.state)
		}
		fmt.Fprintf(&workbook, `<sheet name="%s" sheetId="%d" r:id="rId%d"%s/>`, sheet.name, i+1, i+1, state)
		fmt.Fprintf(&rels, `<Relationship Id="rId%d" Target="worksheets/sheet%d.xml"/>`, i+1, i+1)
		content := sheetXML
		if i > 0 {
			content = `<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">` +
				`<sheetData/></worksheet>`
		}
		entries[fmt.Sprintf("xl/worksheets/sheet%d.xml", i+1)] = content
	}
	workbook.WriteString(`</sheets></workbook>`)
	rels.WriteString(`<Relationship Id="rIdShared" Target="sharedStrings.xml"/></Relationships>`)
	entries[xlsxPathWorkbook] = workbook.String()
	entries[xlsxPathWorkbookRels] = rels.String()

	writeTestZip(t, filePath, entries)
}

func writeTestZip(t *testing.T, filePath string, entries map[string]string) {
	t.Helper()

	var buf bytes.Buffer
	writer := zip.NewWriter(&buf)
	for name, content := range entries {
		entry, err := writer.Create(name)
		if err != nil {
			t.Fatalf("create zip entry %s failed: %s", name, err)
		}
		if _, err := entry.Write([]byte(content)); err != nil {
			t.Fatalf("write zip entry %s failed: %s", name, err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("close zip failed: %s", err)
	}

	if err := os.WriteFile(filePath, buf.Bytes(), 0o644); err != nil {
		t.Fatalf("write xlsx failed: %s", err)
	}
}

type testXlsxRun struct {
	dir    string
	input  string
	output string
	report string
	text   string
	err    error
}

func newTestXlsxOptions(dir string, fileName string) XlsxTemplateOptions {
	return XlsxTemplateOptions{
		Output:        filepath.Join(dir, "whitelist.jsonl"),
		XlsxFile:      filepath.Join(dir, fileName),
		SwitchVersion: "v2",
		Status:        "enabled",
	}
}

func runTestXlsx(t *testing.T, book testXlsxBook, mutate func(*XlsxTemplateOptions)) testXlsxRun {
	t.Helper()

	dir := t.TempDir()
	opts := newTestXlsxOptions(dir, testXlsxFileName)
	if mutate != nil {
		mutate(&opts)
	}
	writeTestXlsx(t, opts.XlsxFile, book)

	var out bytes.Buffer
	opts.Out = &out
	err := CreateImportTemplateFromXlsx(opts)
	report := opts.Report
	if report == "" {
		report = opts.Output + xlsxReportSuffix
	}

	return testXlsxRun{
		dir: dir, input: opts.XlsxFile, output: opts.Output, report: report, text: out.String(), err: err,
	}
}

func readTestRecords(t *testing.T, filePath string) []importAddTemplateRecord {
	t.Helper()

	content, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("read output failed: %s", err)
	}

	records := make([]importAddTemplateRecord, 0)
	for _, line := range strings.Split(strings.TrimSpace(string(content)), "\n") {
		var record importAddTemplateRecord
		if err := json.Unmarshal([]byte(line), &record); err != nil {
			t.Fatalf("unmarshal output line %s failed: %s", line, err)
		}
		records = append(records, record)
	}

	return records
}

func testRecord(clusterID int, domain string, cloud int) importAddTemplateRecord {
	return importAddTemplateRecord{
		Action:        importActionAdd,
		BkBizID:       591,
		BkCloudID:     cloud,
		ClusterID:     clusterID,
		ClusterName:   domain,
		SwitchVersion: "v2",
		Status:        "enabled",
	}
}

func assertXlsxError(t *testing.T, err error, want string) {
	t.Helper()

	if err == nil {
		t.Fatalf("error = nil, want %s", want)
	}
	if !strings.Contains(err.Error(), want) {
		t.Fatalf("error = %s, want contains %s", err, want)
	}
}

func assertNoXlsxOutputs(t *testing.T, run testXlsxRun) {
	t.Helper()

	for _, filePath := range []string{run.output, run.output + xlsxTempSuffix, run.report} {
		if _, err := os.Stat(filePath); !os.IsNotExist(err) {
			t.Fatalf("file %s exists = %v, want not exist", filePath, err)
		}
	}
}

func TestXlsxShuffledColumnsAndCellKinds(t *testing.T) {
	t.Parallel()

	book := testXlsxBook{rows: []testXlsxRow{
		{cells: []testXlsxCell{
			{col: "A", kind: xlsxCellTypeShared, value: "管控区域"},
			{col: "B", kind: xlsxCellTypeInline, value: "主域名"},
			{col: "D", kind: xlsxCellTypeFormula, value: "集群 ID"},
		}},
		{cells: []testXlsxCell{
			{col: "A", kind: xlsxCellTypeNumber, value: "1"},
			{col: "B", kind: xlsxCellTypeShared, value: "a.example.db"},
			{col: "D", kind: xlsxCellTypeNumber, value: "1001"},
		}},
		{cells: []testXlsxCell{
			{col: "A", kind: xlsxCellTypeFormula, value: "0"},
			{col: "B", kind: xlsxCellTypeInline, value: "b.example.db"},
			{col: "D", kind: xlsxCellTypeShared, value: "1002.0"},
		}},
	}}

	run := runTestXlsx(t, book, nil)
	if run.err != nil {
		t.Fatalf("create from xlsx failed: %s, report: %s", run.err, run.text)
	}

	got := readTestRecords(t, run.output)
	want := []importAddTemplateRecord{testRecord(1001, "a.example.db", 1), testRecord(1002, "b.example.db", 0)}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("records = %+v, want %+v", got, want)
	}
}

func TestXlsxMissingCellsDoNotShiftColumns(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "备注", "主域名", "其他", "管控区域"}
	book := testXlsxBook{rows: []testXlsxRow{
		testHeaderRow(headers),
		{cells: []testXlsxCell{
			{col: "A", kind: xlsxCellTypeNumber, value: "1001"},
			{col: "C", kind: xlsxCellTypeShared, value: "a.example.db"},
			{col: "E", kind: xlsxCellTypeNumber, value: "2"},
		}},
	}}

	run := runTestXlsx(t, book, nil)
	if run.err != nil {
		t.Fatalf("create from xlsx failed: %s", run.err)
	}

	got := readTestRecords(t, run.output)
	want := []importAddTemplateRecord{testRecord(1001, "a.example.db", 2)}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("records = %+v, want %+v", got, want)
	}
}

func TestXlsxSkipsEmptyRows(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "主域名", "管控区域"}
	book := testXlsxBook{rows: []testXlsxRow{
		testHeaderRow(headers),
		{cells: []testXlsxCell{{col: "A", kind: xlsxCellTypeInline, value: "  "}}},
		testClusterRow(headers, testCluster{id: "1001", domain: "a.example.db", cloud: "0"}),
		{},
	}}

	run := runTestXlsx(t, book, nil)
	if run.err != nil {
		t.Fatalf("create from xlsx failed: %s", run.err)
	}
	if !strings.Contains(run.text, "source_rows: 3, data_rows: 1, empty_rows: 2") {
		t.Fatalf("report = %s, want source_rows: 3, data_rows: 1, empty_rows: 2", run.text)
	}
}

func TestXlsxSharedStringSkipsPhonetic(t *testing.T) {
	t.Parallel()

	book := testXlsxBook{rows: []testXlsxRow{
		{cells: []testXlsxCell{
			{col: "A", kind: "sraw", value: `<r><t>集群</t></r><r><t> ID</t></r><rPh sb="0" eb="2"><t>ジ</t></rPh>`},
			{col: "B", kind: "sraw", value: `<t>主域名</t><rPh sb="0" eb="1"><t>シュ</t></rPh>`},
			{col: "C", kind: xlsxCellTypeShared, value: "管控区域"},
		}},
		{cells: []testXlsxCell{
			{col: "A", kind: xlsxCellTypeNumber, value: "1001"},
			{col: "B", kind: "sraw", value: `<t>a.example.db</t><rPh sb="0" eb="1"><t>エー</t></rPh>`},
			{col: "C", kind: xlsxCellTypeNumber, value: "0"},
		}},
	}}

	run := runTestXlsx(t, book, nil)
	if run.err != nil {
		t.Fatalf("create from xlsx failed: %s", run.err)
	}

	got := readTestRecords(t, run.output)
	if len(got) != 1 || got[0].ClusterName != "a.example.db" {
		t.Fatalf("records = %+v, want cluster_name a.example.db", got)
	}
}

func TestXlsxNormalizeDomain(t *testing.T) {
	t.Parallel()

	tests := []struct {
		raw         string
		wantDomain  string
		wantRemoved bool
		wantReason  string
	}{
		{raw: " a.example.db ", wantDomain: "a.example.db"},
		{raw: "A.Example.db", wantDomain: "A.Example.db"},
		{raw: "a.example.db:3306", wantDomain: "a.example.db", wantRemoved: true},
		{raw: "a.example.db:abc", wantReason: xlsxReasonInvalidPort},
		{raw: "a.example.db:", wantReason: xlsxReasonInvalidPort},
		{raw: "a.example.db:1:2", wantReason: xlsxReasonInvalidPort},
		{raw: ":3306", wantReason: xlsxReasonRequired},
		{raw: "a.example.db\nb.example.db", wantReason: xlsxReasonMultiDomain},
		{raw: "a.example.db,b.example.db", wantReason: xlsxReasonMultiDomain},
		{raw: "a.example.db;b.example.db", wantReason: xlsxReasonMultiDomain},
		{raw: "a.example.db b.example.db", wantReason: xlsxReasonMultiDomain},
		{raw: "   ", wantReason: xlsxReasonRequired},
	}

	for _, tt := range tests {
		domain, removed, reason := normalizeXlsxDomain(tt.raw)
		if domain != tt.wantDomain || removed != tt.wantRemoved || reason != tt.wantReason {
			t.Fatalf("normalize %q = %q/%v/%q, want %q/%v/%q",
				tt.raw, domain, removed, reason, tt.wantDomain, tt.wantRemoved, tt.wantReason)
		}
	}
}

func TestXlsxDomainErrorsAbortGeneration(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "主域名", "管控区域"}
	for _, domain := range []string{"a.example.db:abc", "a.example.db,b.example.db"} {
		book := testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
			{id: "1001", domain: domain, cloud: "0"},
		})}
		run := runTestXlsx(t, book, nil)
		assertXlsxError(t, run.err, "row: 2, column: 主域名/Primary domain name")
		assertNoXlsxOutputs(t, run)
	}

	book := testXlsxBook{rows: []testXlsxRow{
		testHeaderRow(headers),
		{cells: []testXlsxCell{{col: "A", kind: xlsxCellTypeNumber, value: "1001"}, {col: "C", kind: "n", value: "0"}}},
	}}
	run := runTestXlsx(t, book, nil)
	assertXlsxError(t, run.err, xlsxReasonRequired)
}

func TestXlsxResolveBkBizID(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		file     string
		flag     int
		flagSet  bool
		wantID   int
		wantFrom string
		wantErr  string
	}{
		{name: "timestamp", file: "/tmp/x/mapleleaf(591)mysql_cluster_20261104101251.xlsx", wantID: 591,
			wantFrom: xlsxBizFromFilename},
		{name: "no timestamp", file: "mapleleaf(591)mysql_cluster.xlsx", wantID: 591, wantFrom: xlsxBizFromFilename},
		{name: "biz name has digits", file: "biz(12)name(591)mysql_cluster.xlsx", wantID: 591,
			wantFrom: xlsxBizFromFilename},
		{name: "browser suffix", file: "mapleleaf(591)mysql_cluster (1).xlsx", wantErr: "set --xlsx-bk-biz-id"},
		{name: "flag wins", file: "mapleleaf(591)mysql_cluster.xlsx", flag: 7, flagSet: true, wantID: 7,
			wantFrom: xlsxBizFromFlag},
		{name: "flag zero", file: "mapleleaf(591)mysql_cluster.xlsx", flagSet: true, wantErr: errXlsxBkBizIDInvalid},
	}

	for _, tt := range tests {
		id, from, err := resolveXlsxBkBizID(XlsxTemplateOptions{XlsxFile: tt.file, BkBizID: tt.flag,
			BkBizIDSet: tt.flagSet})
		if tt.wantErr != "" {
			assertXlsxError(t, err, tt.wantErr)
			continue
		}
		if err != nil || id != tt.wantID || from != tt.wantFrom {
			t.Fatalf("%s: biz = %d/%s/%v, want %d/%s/nil", tt.name, id, from, err, tt.wantID, tt.wantFrom)
		}
	}
}

func TestXlsxHeaderRequiredAndOptionalColumns(t *testing.T) {
	t.Parallel()

	for _, missing := range []int{xlsxColClusterID, xlsxColDomain, xlsxColBkCloudID} {
		headers := make([]string, 0)
		for _, header := range []string{"集群 ID", "主域名", "管控区域"} {
			if !matchXlsxHeader(header, xlsxColumnSpecs[missing].aliases) {
				headers = append(headers, header)
			}
		}
		run := runTestXlsx(t, testXlsxBook{rows: []testXlsxRow{testHeaderRow(headers)}}, nil)
		assertXlsxError(t, run.err, fmt.Sprintf(errXlsxHeaderMissingFmt, xlsxColumnLabel(missing)))
	}

	headers := []string{"集群 ID", "主域名", "管控区域"}
	book := testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
		{id: "1001", domain: "a.example.db", cloud: "0"},
	})}
	run := runTestXlsx(t, book, nil)
	if run.err != nil {
		t.Fatalf("create without optional columns failed: %s", run.err)
	}
	if strings.Contains(run.text, msgXlsxStatByType) || strings.Contains(run.text, msgXlsxStatByStatus) {
		t.Fatalf("report = %s, want no cluster type or status stats", run.text)
	}
}

func TestXlsxHeaderBilingual(t *testing.T) {
	t.Parallel()

	for _, headers := range [][]string{
		{"集群 ID", "主域名", "管控区域"},
		{"Cluster ID", "Primary domain name", "control area"},
		{" CLUSTER id ", "primary DOMAIN name", "Control Area"},
	} {
		book := testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
			{id: "1001", domain: "a.example.db", cloud: "0"},
		})}
		run := runTestXlsx(t, book, nil)
		if run.err != nil {
			t.Fatalf("headers %v failed: %s", headers, run.err)
		}
	}

	book := testXlsxBook{rows: []testXlsxRow{testHeaderRow([]string{"集群 ID", "主域名", "管控区域", "Cluster ID"})}}
	run := runTestXlsx(t, book, nil)
	assertXlsxError(t, run.err, fmt.Sprintf(errXlsxHeaderDuplicateFmt, xlsxColumnLabel(xlsxColClusterID)))
}

func TestXlsxInvalidClusterID(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "主域名", "管控区域"}
	for _, id := range []string{"abc", "0", "-1", "1.5", "1e3"} {
		book := testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
			{id: id, domain: "a.example.db", cloud: "0"},
		})}
		run := runTestXlsx(t, book, nil)
		assertXlsxError(t, run.err, xlsxReasonPositiveInt)
	}
}

func TestXlsxDuplicateRows(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "主域名", "管控区域"}
	merged := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
		{id: "1001", domain: "a.example.db", cloud: "0"},
		{id: "1001", domain: "a.example.db:3306", cloud: "0"},
	})}, nil)
	if merged.err != nil {
		t.Fatalf("merge duplicate failed: %s", merged.err)
	}
	if got := readTestRecords(t, merged.output); len(got) != 1 {
		t.Fatalf("records = %d, want 1", len(got))
	}

	tests := []struct {
		clusters []testCluster
		want     string
	}{
		{clusters: []testCluster{{id: "1001", domain: "a.example.db", cloud: "0"},
			{id: "1001", domain: "b.example.db", cloud: "0"}}, want: xlsxReasonIDNameConfl},
		{clusters: []testCluster{{id: "1001", domain: "a.example.db", cloud: "0"},
			{id: "1002", domain: "a.example.db", cloud: "0"}}, want: xlsxReasonNameIDConfl},
		{clusters: []testCluster{{id: "1001", domain: "a.example.db", cloud: "0"},
			{id: "1001", domain: "a.example.db", cloud: "1"}}, want: xlsxReasonIDCloudConfl},
	}
	for _, tt := range tests {
		run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(headers, tt.clusters)}, nil)
		assertXlsxError(t, run.err, "row: 3, conflict row: 2, errmsg: "+tt.want)
		assertNoXlsxOutputs(t, run)
	}
}

func TestXlsxBkCloudIDPerRow(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "主域名", "管控区域"}
	run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
		{id: "1001", domain: "a.example.db", cloud: "0.0"},
		{id: "1002", domain: "b.example.db", cloud: "1"},
		{id: "1003", domain: "c.example.db", cloud: "0"},
	})}, nil)
	if run.err != nil {
		t.Fatalf("create from xlsx failed: %s", run.err)
	}

	got := readTestRecords(t, run.output)
	want := []importAddTemplateRecord{
		testRecord(1001, "a.example.db", 0), testRecord(1002, "b.example.db", 1), testRecord(1003, "c.example.db", 0),
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("records = %+v, want %+v", got, want)
	}

	for _, cloud := range []string{"x", "-1", "1.5"} {
		bad := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
			{id: "1001", domain: "a.example.db", cloud: cloud},
		})}, nil)
		assertXlsxError(t, bad.err, xlsxReasonNonNegInt)
	}

	empty := runTestXlsx(t, testXlsxBook{rows: []testXlsxRow{
		testHeaderRow(headers),
		{cells: []testXlsxCell{{col: "A", kind: "n", value: "1001"}, {col: "B", kind: "s", value: "a.example.db"}}},
	}}, nil)
	assertXlsxError(t, empty.err, "column: 管控区域/control area, value: \"\", errmsg: "+xlsxReasonRequired)
}

func TestXlsxDBMHeaderOrder(t *testing.T) {
	t.Parallel()

	withoutDynamic := make([]string, 0, len(testDBMHeadersZh))
	for _, header := range testDBMHeadersZh {
		if header != "clb" && header != "Master" && header != "Slave" && header != "Proxy" {
			withoutDynamic = append(withoutDynamic, header)
		}
	}

	for _, headers := range [][]string{testDBMHeadersZh, withoutDynamic} {
		run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
			{id: "1001", domain: "a.example.db", cloud: "1", clusterType: "tendbha", status: "正常"},
		})}, nil)
		if run.err != nil {
			t.Fatalf("headers %d columns failed: %s", len(headers), run.err)
		}
		got := readTestRecords(t, run.output)
		if !reflect.DeepEqual(got, []importAddTemplateRecord{testRecord(1001, "a.example.db", 1)}) {
			t.Fatalf("headers %d columns records = %+v", len(headers), got)
		}
	}
}

func TestXlsxHeaderOnly(t *testing.T) {
	t.Parallel()

	run := runTestXlsx(t, testXlsxBook{rows: []testXlsxRow{testHeaderRow(testDBMHeadersZh)}}, nil)
	assertXlsxError(t, run.err, errXlsxNoDataRows)
	assertNoXlsxOutputs(t, run)

	empty := runTestXlsx(t, testXlsxBook{}, nil)
	assertXlsxError(t, empty.err, errXlsxHeaderRequired)
}

func TestXlsxWorkbookSheets(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "主域名", "管控区域"}
	rows := testRowsFromClusters(headers, []testCluster{{id: "1001", domain: "a.example.db", cloud: "0"}})

	multi := runTestXlsx(t, testXlsxBook{rows: rows, sheets: []testXlsxSheet{{name: "Sheet"}, {name: "Other"}}}, nil)
	assertXlsxError(t, multi.err, fmt.Sprintf(errXlsxMultipleSheetsFmt, "Sheet, Other"))

	hidden := runTestXlsx(t, testXlsxBook{rows: rows, sheets: []testXlsxSheet{
		{name: "Sheet"}, {name: "Hidden", state: "veryHidden"},
	}}, nil)
	assertXlsxError(t, hidden.err, fmt.Sprintf(errXlsxMultipleSheetsFmt, "Sheet, Hidden"))
	assertNoXlsxOutputs(t, hidden)
}

func TestXlsxHiddenRowsAndColumns(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "主域名", "管控区域"}
	rows := testRowsFromClusters(headers, []testCluster{
		{id: "1001", domain: "a.example.db", cloud: "0"},
		{id: "1002", domain: "b.example.db", cloud: "0"},
		{id: "1003", domain: "c.example.db", cloud: "0"},
	})
	rows[1].hidden = xlsxBoolOne
	rows[3].hidden = xlsxBoolTrue

	run := runTestXlsx(t, testXlsxBook{rows: rows}, nil)
	assertXlsxError(t, run.err, fmt.Sprintf(errXlsxHiddenRowsFmt, "2, 4"))
	assertNoXlsxOutputs(t, run)

	visible := testRowsFromClusters(headers, []testCluster{{id: "1001", domain: "a.example.db", cloud: "0"}})
	visible = append(visible, testXlsxRow{hidden: xlsxBoolOne})
	ok := runTestXlsx(t, testXlsxBook{
		rows:        visible,
		sheetPrefix: `<cols><col min="2" max="2" width="10" hidden="1"/></cols>`,
	}, nil)
	if ok.err != nil {
		t.Fatalf("hidden empty row and hidden column failed: %s", ok.err)
	}
	if !strings.Contains(ok.text, "empty_rows: 1") {
		t.Fatalf("report = %s, want empty_rows: 1", ok.text)
	}
}

func TestXlsxUnsupportedCellTypes(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "主域名", "管控区域", "状态", "备注"}
	for _, kind := range []string{xlsxCellTypeBool, xlsxCellTypeError, xlsxCellTypeDate} {
		book := testXlsxBook{rows: []testXlsxRow{
			testHeaderRow(headers),
			{cells: []testXlsxCell{
				{col: "A", kind: xlsxCellTypeNumber, value: "1001"},
				{col: "B", kind: xlsxCellTypeShared, value: "a.example.db"},
				{col: "C", kind: kind, value: "#N/A"},
			}},
		}}
		run := runTestXlsx(t, book, nil)
		assertXlsxError(t, run.err, fmt.Sprintf(errXlsxUnsupportedCellFmt, 2, xlsxColumnLabel(xlsxColBkCloudID), kind))

		ignored := testXlsxBook{rows: []testXlsxRow{
			testHeaderRow(headers),
			{cells: []testXlsxCell{
				{col: "A", kind: xlsxCellTypeNumber, value: "1001"},
				{col: "B", kind: xlsxCellTypeShared, value: "a.example.db"},
				{col: "C", kind: xlsxCellTypeNumber, value: "0"},
				{col: "D", kind: kind, value: "#N/A"},
				{col: "E", kind: kind, value: "1"},
			}},
		}}
		okRun := runTestXlsx(t, ignored, nil)
		if okRun.err != nil {
			t.Fatalf("optional %s cell failed: %s", kind, okRun.err)
		}
	}
}

func TestXlsxGeneratedFileImportDryRun(t *testing.T) {
	t.Parallel()

	run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(testDBMHeadersZh, []testCluster{
		{id: "1001", domain: "a.example.db:3306", cloud: "1", clusterType: "tendbha", status: "正常"},
		{id: "1002", domain: "b.example.db", cloud: "0", clusterType: "tendbha", status: "正常"},
	})}, nil)
	if run.err != nil {
		t.Fatalf("create from xlsx failed: %s", run.err)
	}

	service := &fakeBlackWhiteListService{}
	h := NewHandlerWithService(0, service)
	if err := h.Import(ImportOptions{File: run.output, DryRun: true}); err != nil {
		t.Fatalf("import dry run failed: %s", err)
	}
	if service.getCalls != 0 || len(service.insertRequests) != 0 {
		t.Fatalf("service calls get/insert = %d/%d, want 0/0", service.getCalls, len(service.insertRequests))
	}

	entries, err := readImportEntries(run.output)
	if err != nil {
		t.Fatalf("read generated file failed: %s", err)
	}
	if entries[0].Record.ClusterName != "a.example.db" || entries[0].Record.BkCloudID != 1 {
		t.Fatalf("first record = %+v, want a.example.db/1", entries[0].Record)
	}
	if entries[1].Record.ClusterName != "b.example.db" || entries[1].Record.BkCloudID != 0 {
		t.Fatalf("second record = %+v, want b.example.db/0", entries[1].Record)
	}
}

func TestXlsxRejectsOversizedEntry(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	filePath := filepath.Join(dir, testXlsxFileName)
	writeTestZip(t, filePath, map[string]string{xlsxPathWorkbook: strings.Repeat(" ", xlsxMaxEntrySize+1)})

	opts := newTestXlsxOptions(dir, testXlsxFileName)
	err := CreateImportTemplateFromXlsx(opts)
	assertXlsxError(t, err, fmt.Sprintf(errXlsxEntryTooLargeFmt, xlsxPathWorkbook, xlsxMaxEntrySize))
}

func TestXlsxRejectsIntegerOverflow(t *testing.T) {
	t.Parallel()

	if want := "must not exceed " + strconv.Itoa(math.MaxInt32); xlsxReasonIntRange != want {
		t.Fatalf("int range reason = %q, want %q", xlsxReasonIntRange, want)
	}

	headers := []string{"集群 ID", "主域名", "管控区域"}
	overflow := strconv.Itoa(math.MaxInt32 + 1)
	tests := []struct {
		name    string
		cluster testCluster
		column  string
	}{
		{name: "cluster id", cluster: testCluster{id: overflow, domain: "a.example.db", cloud: "0"},
			column: "row: 2, column: 集群 ID/Cluster ID"},
		{name: "bk cloud id", cluster: testCluster{id: "1001", domain: "a.example.db", cloud: overflow + ".0"},
			column: "row: 2, column: 管控区域/control area"},
	}
	for _, tt := range tests {
		run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{tt.cluster})}, nil)
		assertXlsxError(t, run.err, tt.column)
		assertXlsxError(t, run.err, xlsxReasonIntRange)
		assertNoXlsxOutputs(t, run)
	}

	maxValue := strconv.Itoa(math.MaxInt32)
	run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
		{id: maxValue, domain: "a.example.db", cloud: maxValue},
	})}, nil)
	if run.err != nil {
		t.Fatalf("create with max int32 failed: %s, report: %s", run.err, run.text)
	}
	got := readTestRecords(t, run.output)
	want := []importAddTemplateRecord{testRecord(math.MaxInt32, "a.example.db", math.MaxInt32)}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("records = %+v, want %+v", got, want)
	}
}
