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
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"reflect"
	"testing"
)

var testXlsxShortHeaders = []string{"集群 ID", "主域名", "管控区域"}

// testXlsxGeneratorIdents are generation-side helpers that the verifier must not use to build expected values.
var testXlsxGeneratorIdents = []string{
	"normalizeXlsxDomain", "parseXlsxInteger", "convertXlsxSourceRow", "buildXlsxRecords", "checkXlsxSameCluster",
	"resolveXlsxParams", "resolveXlsxBkBizID", "xlsxIntegerPattern", "xlsxDomainSplitSets",
	"xlsxBizFileNamePattern", "xlsxDomainAllowedChars",
}

// prepareTestVerifySource writes the source xlsx and resolves paths and params without generating the temp file.
func prepareTestVerifySource(t *testing.T, clusters []testCluster) (xlsxPaths, xlsxParams) {
	t.Helper()

	dir := t.TempDir()
	opts := newTestXlsxOptions(dir, testXlsxFileName)
	writeTestXlsx(t, opts.XlsxFile, testXlsxBook{rows: testRowsFromClusters(testXlsxShortHeaders, clusters)})

	paths, err := resolveXlsxPaths(opts)
	if err != nil {
		t.Fatalf("resolve paths failed: %s", err)
	}
	params, err := resolveXlsxParams(opts)
	if err != nil {
		t.Fatalf("resolve params failed: %s", err)
	}

	return paths, params
}

func TestXlsxVerifyDoesNotReuseGenerator(t *testing.T) {
	t.Parallel()

	file, err := parser.ParseFile(token.NewFileSet(), "xlsx_verify.go", nil, 0)
	if err != nil {
		t.Fatalf("parse xlsx_verify.go failed: %s", err)
	}

	forbidden := make(map[string]bool, len(testXlsxGeneratorIdents))
	for _, name := range testXlsxGeneratorIdents {
		forbidden[name] = true
	}

	found := make(map[string]bool)
	ast.Inspect(file, func(node ast.Node) bool {
		if ident, ok := node.(*ast.Ident); ok && forbidden[ident.Name] {
			found[ident.Name] = true
		}
		return true
	})
	if len(found) > 0 {
		t.Fatalf("xlsx_verify.go uses generation helpers %v, expected values must be derived independently", found)
	}
}

func TestXlsxIntParsers(t *testing.T) {
	t.Parallel()

	tests := []struct {
		raw    string
		wantOK bool
		want   int
	}{
		{raw: "123", wantOK: true, want: 123},
		{raw: " 42 ", wantOK: true, want: 42},
		{raw: "007", wantOK: true, want: 7},
		{raw: "123.0", wantOK: true, want: 123},
		{raw: "123.00", wantOK: true, want: 123},
		{raw: "0", wantOK: true, want: 0},
		{raw: "2147483647", wantOK: true, want: 2147483647},
		{raw: "2147483648"},
		{raw: "99999999999999999999999"},
		{raw: "1."},
		{raw: ".5"},
		{raw: "1.0E+2"},
		{raw: "1e3"},
		{raw: "0x10"},
		{raw: "+5"},
		{raw: "-1"},
		{raw: "1.5"},
		{raw: "1.0.0"},
		{raw: ""},
	}

	for _, tt := range tests {
		genValue, reason := parseXlsxInteger(tt.raw, xlsxReasonNonNegInt)
		if genOK := reason == ""; genOK != tt.wantOK || (genOK && genValue != tt.want) {
			t.Fatalf("generation parse %q = %d/%q, want ok: %v, value: %d", tt.raw, genValue, reason, tt.wantOK, tt.want)
		}

		verifyValue := verifyParseXlsxInt(tt.raw)
		if verifyOK := verifyValue != -1; verifyOK != tt.wantOK || (verifyOK && verifyValue != tt.want) {
			t.Fatalf("verify parse %q = %d, want ok: %v, value: %d", tt.raw, verifyValue, tt.wantOK, tt.want)
		}
	}
}

func TestXlsxVerifyCatchesBkBizIDDrift(t *testing.T) {
	t.Parallel()

	paths, params := prepareTestVerifySource(t, testVerifyClusters)
	if params.BkBizID != 591 || params.BkBizIDFrom != xlsxBizFromFilename {
		t.Fatalf("params = %+v, want bk_biz_id 591 from filename", params)
	}

	params.BkBizID = 592
	src, err := readXlsxSource(paths.Input)
	if err != nil {
		t.Fatalf("read source failed: %s", err)
	}
	records, err := buildXlsxRecords(src, params)
	if err != nil {
		t.Fatalf("build records failed: %s", err)
	}
	if err := writeXlsxTemplateTemp(paths.Temp, records); err != nil {
		t.Fatalf("write temp failed: %s", err)
	}

	result := runTestVerify(t, paths, params)
	assertTestVerifyFailed(t, paths, result)

	mismatches := testMismatches(result.report, xlsxCheckIDC5)
	if len(mismatches) != len(testVerifyClusters) {
		t.Fatalf("C5 mismatches = %+v, want one per row", mismatches)
	}
	for _, mismatch := range mismatches {
		if mismatch.Field != xlsxFieldBkBizID || mismatch.Expected != "591" || mismatch.JSON != "592" {
			t.Fatalf("C5 mismatch = %+v, want bk_biz_id expected 591 json 592", mismatch)
		}
	}
}

func TestXlsxVerifyCatchesMergeConflict(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		second   testCluster
		field    string
		xlsx     string
		expected string
	}{
		{name: "domain", second: testCluster{id: "1001", domain: "b.example.db", cloud: "0"},
			field: xlsxFieldClusterName, xlsx: "b.example.db", expected: "a.example.db"},
		{name: "cloud", second: testCluster{id: "1001", domain: "a.example.db", cloud: "1"},
			field: xlsxFieldBkCloudID, xlsx: "1", expected: "0"},
	}

	for _, tt := range tests {
		paths, params := prepareTestVerifySource(t, []testCluster{
			{id: "1001", domain: "a.example.db", cloud: "0"}, tt.second,
		})
		records := []importAddTemplateRecord{testRecord(1001, "a.example.db", 0)}
		if err := writeXlsxTemplateTemp(paths.Temp, records); err != nil {
			t.Fatalf("%s: write temp failed: %s", tt.name, err)
		}

		result := runTestVerify(t, paths, params)
		assertTestVerifyFailed(t, paths, result)
		if failed := failedTestChecks(result.report); !reflect.DeepEqual(failed, []string{xlsxCheckIDC3}) {
			t.Fatalf("%s: failed checks = %v, want [C3]", tt.name, failed)
		}

		want := []xlsxMismatch{{
			Check: xlsxCheckIDC3, Row: 3, ClusterID: 1001, Field: tt.field, Xlsx: tt.xlsx, Expected: tt.expected,
			Reason: xlsxReasonMergeConfl,
		}}
		if got := testMismatches(result.report, xlsxCheckIDC3); !reflect.DeepEqual(got, want) {
			t.Fatalf("%s: C3 mismatches = %+v, want %+v", tt.name, got, want)
		}
		if check := testCheck(t, result.report, xlsxCheckIDC3); check.Passed != 1 || check.Total != 2 {
			t.Fatalf("%s: C3 = %d/%d, want 1/2", tt.name, check.Passed, check.Total)
		}
	}

	run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(testXlsxShortHeaders, []testCluster{
		{id: "1001", domain: "a.example.db", cloud: "0"},
		{id: "1001", domain: "a.example.db:3306", cloud: "0.0"},
	})}, nil)
	if run.err != nil {
		t.Fatalf("legitimate merge failed: %s, report: %s", run.err, run.text)
	}
	report := readTestReport(t, run.report)
	if mismatches := testMismatches(report, xlsxCheckIDC3); len(mismatches) != 0 {
		t.Fatalf("legitimate merge C3 mismatches = %+v, want none", mismatches)
	}
	if got := readTestRecords(t, run.output); !reflect.DeepEqual(got, []importAddTemplateRecord{
		testRecord(1001, "a.example.db", 0),
	}) {
		t.Fatalf("legitimate merge records = %+v", got)
	}
}

func TestXlsxHeaderCheckedBeforeHiddenRows(t *testing.T) {
	t.Parallel()

	headers := []string{"集群 ID", "主域名"}
	rows := testRowsFromClusters(headers, []testCluster{
		{id: "1001", domain: "a.example.db"},
		{id: "1002", domain: "b.example.db"},
	})
	rows[2].hidden = xlsxBoolOne

	run := runTestXlsx(t, testXlsxBook{rows: rows}, nil)
	assertXlsxError(t, run.err, fmt.Sprintf(errXlsxHeaderMissingFmt, xlsxColumnLabel(xlsxColBkCloudID)))
	assertNoXlsxOutputs(t, run)
}

func TestXlsxHiddenRowCheckedBeforeCellTypes(t *testing.T) {
	t.Parallel()

	book := testXlsxBook{rows: []testXlsxRow{
		testHeaderRow(testXlsxShortHeaders),
		{hidden: xlsxBoolOne, cells: []testXlsxCell{
			{col: "A", kind: xlsxCellTypeNumber, value: "1001"},
			{col: "B", kind: xlsxCellTypeShared, value: "a.example.db"},
			{col: "C", kind: xlsxCellTypeBool, value: "1"},
		}},
	}}

	run := runTestXlsx(t, book, nil)
	assertXlsxError(t, run.err, fmt.Sprintf(errXlsxHiddenRowsFmt, "2"))
	assertNoXlsxOutputs(t, run)
}

func TestXlsxRejectsInvalidDomainChars(t *testing.T) {
	t.Parallel()

	for _, domain := range []string{"a.example.db\u3000b.example.db", "a.example\u200b.db"} {
		run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(testXlsxShortHeaders, []testCluster{
			{id: "1001", domain: domain, cloud: "0"},
		})}, nil)
		assertXlsxError(t, run.err, "row: 2, column: 主域名/Primary domain name")
		assertXlsxError(t, run.err, "must contain only letters, digits, '.', '-' or '_'")
		assertNoXlsxOutputs(t, run)
	}
}
