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
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"
)

const testVerifyFirstLine = `{"action":"add","bk_biz_id":591,"bk_cloud_id":1,"cluster_id":1001,` +
	`"cluster_name":"a.example.db","switch_version":"v2","status":"enabled"}`

var testVerifyClusters = []testCluster{
	{id: "1001", domain: "a.example.db", cloud: "1", clusterType: "tendbha", status: "正常"},
	{id: "1002", domain: "b.example.db", cloud: "0", clusterType: "tendbha", status: "正常"},
	{id: "1003", domain: "c.example.db", cloud: "0", clusterType: "tendbha", status: "正常"},
}

var testCheckIDs = []string{
	xlsxCheckIDC1, xlsxCheckIDC2, xlsxCheckIDC3, xlsxCheckIDC4, xlsxCheckIDC5, xlsxCheckIDC6, xlsxCheckIDC7,
}

type testVerifyResult struct {
	report xlsxVerifyReport
	text   string
	err    error
}

func prepareTestVerify(t *testing.T, clusters []testCluster) (xlsxPaths, xlsxParams) {
	t.Helper()

	dir := t.TempDir()
	opts := newTestXlsxOptions(dir, testXlsxFileName)
	writeTestXlsx(t, opts.XlsxFile, testXlsxBook{rows: testRowsFromClusters(testDBMHeadersZh, clusters)})

	paths, err := resolveXlsxPaths(opts)
	if err != nil {
		t.Fatalf("resolve paths failed: %s", err)
	}
	params, err := resolveXlsxParams(opts)
	if err != nil {
		t.Fatalf("resolve params failed: %s", err)
	}
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

	return paths, params
}

func tamperTestTemp(t *testing.T, filePath string, mutate func([]string) []string) {
	t.Helper()

	content, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("read temp failed: %s", err)
	}

	lines := mutate(strings.Split(strings.TrimSuffix(string(content), "\n"), "\n"))
	if err := os.WriteFile(filePath, []byte(strings.Join(lines, "\n")+"\n"), 0o644); err != nil {
		t.Fatalf("write temp failed: %s", err)
	}
}

func replaceTestLine(index int, old string, replacement string) func([]string) []string {
	return func(lines []string) []string {
		lines[index] = strings.Replace(lines[index], old, replacement, 1)
		return lines
	}
}

func runTestVerify(t *testing.T, paths xlsxPaths, params xlsxParams) testVerifyResult {
	t.Helper()

	var out bytes.Buffer
	err := verifyAndFinalizeXlsxTemplate(paths, params, &out)

	return testVerifyResult{report: readTestReport(t, paths.Report), text: out.String(), err: err}
}

func readTestReport(t *testing.T, reportPath string) xlsxVerifyReport {
	t.Helper()

	content, err := os.ReadFile(reportPath)
	if err != nil {
		t.Fatalf("read report failed: %s", err)
	}

	var report xlsxVerifyReport
	if err := json.Unmarshal(content, &report); err != nil {
		t.Fatalf("unmarshal report failed: %s", err)
	}

	return report
}

func testCheck(t *testing.T, report xlsxVerifyReport, id string) xlsxCheckResult {
	t.Helper()

	for _, check := range report.Checks {
		if check.ID == id {
			return check
		}
	}
	t.Fatalf("check %s not found in %+v", id, report.Checks)

	return xlsxCheckResult{}
}

func testMismatches(report xlsxVerifyReport, check string) []xlsxMismatch {
	mismatches := make([]xlsxMismatch, 0)
	for _, mismatch := range report.Mismatches {
		if mismatch.Check == check {
			mismatches = append(mismatches, mismatch)
		}
	}

	return mismatches
}

func failedTestChecks(report xlsxVerifyReport) []string {
	failed := make([]string, 0)
	for _, check := range report.Checks {
		if check.Result != xlsxResultPass {
			failed = append(failed, check.ID)
		}
	}
	sort.Strings(failed)

	return failed
}

func assertTestVerifyFailed(t *testing.T, paths xlsxPaths, result testVerifyResult) {
	t.Helper()

	assertXlsxError(t, result.err, fmt.Sprintf(errXlsxVerifyFailedFmt, paths.Report))
	if result.report.Result != xlsxResultFail || !strings.Contains(result.text, "result: FAIL") {
		t.Fatalf("result = %s, text = %s, want FAIL", result.report.Result, result.text)
	}
	if _, err := os.Stat(paths.Temp); !os.IsNotExist(err) {
		t.Fatalf("temp exists = %v, want removed", err)
	}
	if _, err := os.Stat(paths.Output); !os.IsNotExist(err) {
		t.Fatalf("output exists = %v, want not written", err)
	}
	if result.report.OutputWritten || result.report.ExistingOutputKept {
		t.Fatalf("output written/kept = %v/%v, want false/false",
			result.report.OutputWritten, result.report.ExistingOutputKept)
	}
}

func TestXlsxVerifyPassRenamesTemp(t *testing.T) {
	t.Parallel()

	paths, params := prepareTestVerify(t, testVerifyClusters)
	result := runTestVerify(t, paths, params)
	if result.err != nil {
		t.Fatalf("verify failed: %s, report: %s", result.err, result.text)
	}

	if _, err := os.Stat(paths.Temp); !os.IsNotExist(err) {
		t.Fatalf("temp exists = %v, want renamed", err)
	}
	content, err := os.ReadFile(paths.Output)
	if err != nil || !strings.HasPrefix(string(content), testVerifyFirstLine+"\n") {
		t.Fatalf("output = %q/%v, want first line %s", content, err, testVerifyFirstLine)
	}
	if result.report.Result != xlsxResultPass || !result.report.OutputWritten || result.report.ExistingOutputKept {
		t.Fatalf("report result/written/kept = %s/%v/%v, want PASS/true/false",
			result.report.Result, result.report.OutputWritten, result.report.ExistingOutputKept)
	}

	ids := make([]string, 0, len(result.report.Checks))
	for _, check := range result.report.Checks {
		ids = append(ids, check.ID)
	}
	if !reflect.DeepEqual(ids, testCheckIDs) {
		t.Fatalf("check ids = %v, want %v", ids, testCheckIDs)
	}
	if !strings.Contains(result.text, "result: PASS") || !strings.Contains(result.text, "[PASS] C7 count: 3 = 3 + 0") {
		t.Fatalf("text = %s, want PASS lines", result.text)
	}
}

func TestXlsxVerifyReportJSONFields(t *testing.T) {
	t.Parallel()

	paths, params := prepareTestVerify(t, testVerifyClusters)
	result := runTestVerify(t, paths, params)
	if result.err != nil {
		t.Fatalf("verify failed: %s", result.err)
	}

	content, err := os.ReadFile(paths.Report)
	if err != nil {
		t.Fatalf("read report failed: %s", err)
	}
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(content, &raw); err != nil {
		t.Fatalf("unmarshal report failed: %s", err)
	}

	for _, key := range []string{
		"result", "generated_at", "source", "output", "output_written", "existing_output_kept", "params",
		"counts", "checks", "stats", "mismatches", "normalized", "merged", "warnings",
	} {
		if _, ok := raw[key]; !ok {
			t.Fatalf("report key %s missing in %s", key, content)
		}
	}

	want := xlsxReportCounts{SourceRows: 3, DataRows: 3, OutputLines: 3}
	if result.report.Counts != want {
		t.Fatalf("counts = %+v, want %+v", result.report.Counts, want)
	}
	wantParams := xlsxReportParams{BkBizID: 591, BkBizIDFrom: xlsxBizFromFilename, SwitchVersion: "v2",
		Status: "enabled"}
	if result.report.Params != wantParams {
		t.Fatalf("params = %+v, want %+v", result.report.Params, wantParams)
	}
	if info, err := os.Stat(paths.Report); err != nil || info.Mode().Perm() != 0o644 {
		t.Fatalf("report mode = %v/%v, want 0644", info, err)
	}
}

func TestXlsxVerifyUnparsableLine(t *testing.T) {
	t.Parallel()

	paths, params := prepareTestVerify(t, testVerifyClusters)
	tamperTestTemp(t, paths.Temp, func(lines []string) []string {
		lines[0] = "{bad"
		return lines
	})

	result := runTestVerify(t, paths, params)
	assertTestVerifyFailed(t, paths, result)

	if got := testMismatches(result.report, xlsxCheckIDC1); len(got) != 1 || got[0].Line != 1 {
		t.Fatalf("C1 mismatches = %+v, want line 1", got)
	}
	if got := testMismatches(result.report, xlsxCheckIDC2); len(got) != 1 || got[0].Reason != xlsxReasonNotObject {
		t.Fatalf("C2 mismatches = %+v, want not an object", got)
	}
	coverage := testMismatches(result.report, xlsxCheckIDC3)
	if len(coverage) != 1 || coverage[0].Row != 2 || coverage[0].Reason != xlsxReasonMissing {
		t.Fatalf("C3 mismatches = %+v, want row 2 missing in output", coverage)
	}
	if check := testCheck(t, result.report, xlsxCheckIDC5); check.Passed != 2 || check.Total != 2 {
		t.Fatalf("C5 = %+v, want 2/2", check)
	}
}

func TestXlsxVerifyInvalidLineKeepsCounting(t *testing.T) {
	t.Parallel()

	paths, params := prepareTestVerify(t, testVerifyClusters)
	tamperTestTemp(t, paths.Temp, replaceTestLine(0, `"switch_version":"v2"`, `"switch_version":"v3"`))

	result := runTestVerify(t, paths, params)
	assertTestVerifyFailed(t, paths, result)

	want := []string{xlsxCheckIDC1, xlsxCheckIDC3, xlsxCheckIDC7}
	if got := failedTestChecks(result.report); !reflect.DeepEqual(got, want) {
		t.Fatalf("failed checks = %v, want %v", got, want)
	}
	coverage := testMismatches(result.report, xlsxCheckIDC3)
	if len(coverage) != 1 || coverage[0].Row != 2 || coverage[0].Reason != xlsxReasonNoValid {
		t.Fatalf("C3 mismatches = %+v, want row 2 no valid line", coverage)
	}
	for _, id := range []string{xlsxCheckIDC4, xlsxCheckIDC5, xlsxCheckIDC6} {
		if check := testCheck(t, result.report, id); check.Total != 2 || check.Passed != 2 {
			t.Fatalf("%s = %+v, want 2/2", id, check)
		}
	}
	if result.report.Counts.OutputLines != 2 {
		t.Fatalf("output lines = %d, want 2", result.report.Counts.OutputLines)
	}
	if !strings.Contains(result.text, "reason: "+xlsxReasonNoValid) {
		t.Fatalf("text = %s, want %s", result.text, xlsxReasonNoValid)
	}
}

func TestXlsxVerifyStrictFieldSet(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name      string
		mutate    func([]string) []string
		wantField string
		wantWhy   string
		wantC1    bool
	}{
		{name: "missing key", mutate: replaceTestLine(0, `,"status":"enabled"`, ""),
			wantField: xlsxFieldStatus, wantWhy: xlsxReasonMissingKey, wantC1: true},
		{name: "id", mutate: replaceTestLine(0, `{`, `{"id":5,`),
			wantField: "id", wantWhy: xlsxReasonUnexpKey, wantC1: true},
		{name: "set cluster name", mutate: replaceTestLine(0, `{`, `{"set_cluster_name":"x.example.db",`),
			wantField: "set_cluster_name", wantWhy: xlsxReasonUnexpKey, wantC1: true},
		{name: "typo", mutate: replaceTestLine(0, `"bk_cloud_id":1`, `"bk_cloud":1`),
			wantField: "bk_cloud", wantWhy: xlsxReasonUnexpKey, wantC1: true},
		{name: "upper case", mutate: replaceTestLine(0, `"bk_cloud_id"`, `"BK_CLOUD_ID"`),
			wantField: "BK_CLOUD_ID", wantWhy: xlsxReasonUnexpKey, wantC1: true},
		{name: "duplicate", mutate: replaceTestLine(0, `"bk_cloud_id":1`, `"bk_cloud_id":1,"bk_cloud_id":0`),
			wantField: xlsxFieldBkCloudID, wantWhy: xlsxReasonDupKey, wantC1: true},
		{name: "null", mutate: replaceTestLine(0, `"bk_cloud_id":1`, `"bk_cloud_id":null`),
			wantField: xlsxFieldBkCloudID, wantWhy: xlsxReasonNullValue, wantC1: true},
		{name: "number as string", mutate: replaceTestLine(0, `"bk_cloud_id":1`, `"bk_cloud_id":"1"`),
			wantField: xlsxFieldBkCloudID, wantWhy: xlsxReasonTypeMis},
		{name: "string as number", mutate: replaceTestLine(0, `"status":"enabled"`, `"status":1`),
			wantField: xlsxFieldStatus, wantWhy: xlsxReasonTypeMis},
		{name: "float", mutate: replaceTestLine(0, `"bk_cloud_id":1`, `"bk_cloud_id":1.0`),
			wantField: xlsxFieldBkCloudID, wantWhy: xlsxReasonNonInteger},
		{name: "nested", mutate: replaceTestLine(0, `"status":"enabled"`, `"status":{"a":1}`),
			wantField: xlsxFieldStatus, wantWhy: xlsxReasonTypeMis},
		{name: "trailing", mutate: replaceTestLine(0, `"enabled"}`, `"enabled"} {}`),
			wantWhy: xlsxReasonNotObject},
		{name: "array", mutate: func(lines []string) []string { lines[0] = `[1]`; return lines },
			wantWhy: xlsxReasonNotObject},
	}

	for _, tt := range tests {
		paths, params := prepareTestVerify(t, testVerifyClusters)
		tamperTestTemp(t, paths.Temp, tt.mutate)

		result := runTestVerify(t, paths, params)
		assertTestVerifyFailed(t, paths, result)

		strict := testMismatches(result.report, xlsxCheckIDC2)
		if len(strict) != 1 || strict[0].Line != 1 || strict[0].Reason != tt.wantWhy ||
			strict[0].Field != tt.wantField {
			t.Fatalf("%s: C2 mismatches = %+v, want line 1 field %q reason %s",
				tt.name, strict, tt.wantField, tt.wantWhy)
		}
		if c1Passed := len(testMismatches(result.report, xlsxCheckIDC1)) == 0; c1Passed != tt.wantC1 {
			t.Fatalf("%s: C1 passed = %v, want %v", tt.name, c1Passed, tt.wantC1)
		}
	}
}

func TestXlsxVerifyDuplicateKeyOnlyCaughtByC2(t *testing.T) {
	t.Parallel()

	paths, params := prepareTestVerify(t, testVerifyClusters)
	tamperTestTemp(t, paths.Temp, replaceTestLine(1, `"bk_cloud_id":0`, `"bk_cloud_id":1,"bk_cloud_id":0`))

	result := runTestVerify(t, paths, params)
	assertTestVerifyFailed(t, paths, result)

	want := []string{xlsxCheckIDC2, xlsxCheckIDC3, xlsxCheckIDC7}
	if got := failedTestChecks(result.report); !reflect.DeepEqual(got, want) {
		t.Fatalf("failed checks = %v, want %v", got, want)
	}
	if len(testMismatches(result.report, xlsxCheckIDC1)) != 0 {
		t.Fatalf("C1 mismatches = %+v, want none", testMismatches(result.report, xlsxCheckIDC1))
	}
}

func TestXlsxVerifyDetectsTampering(t *testing.T) {
	t.Parallel()

	extraLine := `{"action":"add","bk_biz_id":591,"bk_cloud_id":0,"cluster_id":9999,` +
		`"cluster_name":"x.example.db","switch_version":"v2","status":"enabled"}`
	tests := []struct {
		name       string
		mutate     func([]string) []string
		wantFailed []string
		wantDetail string
	}{
		{name: "delete", mutate: func(lines []string) []string { return append(lines[:1], lines[2:]...) },
			wantFailed: []string{xlsxCheckIDC3, xlsxCheckIDC7},
			wantDetail: "row: 3, cluster_id: 1002, reason: " + xlsxReasonMissing},
		{name: "insert", mutate: func(lines []string) []string { return append(lines, extraLine) },
			wantFailed: []string{xlsxCheckIDC4, xlsxCheckIDC7},
			wantDetail: "line: 4, cluster_id: 9999, reason: " + xlsxReasonNotSource},
		{name: "bk_cloud_id", mutate: replaceTestLine(0, `"bk_cloud_id":1`, `"bk_cloud_id":0`),
			wantFailed: []string{xlsxCheckIDC5},
			wantDetail: "row: 2, line: 1, field: bk_cloud_id, xlsx: 1, expected: 1, json: 0"},
		{name: "cluster_name", mutate: replaceTestLine(0, `"a.example.db"`, `"z.example.db"`),
			wantFailed: []string{xlsxCheckIDC5},
			wantDetail: "field: cluster_name, xlsx: a.example.db, expected: a.example.db, json: z.example.db"},
		{name: "status", mutate: replaceTestLine(0, `"enabled"`, `"disabled"`),
			wantFailed: []string{xlsxCheckIDC5}, wantDetail: "field: status, xlsx: enabled"},
		{name: "duplicate line", mutate: func(lines []string) []string { return append(lines, lines[0]) },
			wantFailed: []string{xlsxCheckIDC6, xlsxCheckIDC7},
			wantDetail: "line: 4, field: cluster_id, json: 1001, reason: duplicate, first line: 1"},
	}

	for _, tt := range tests {
		paths, params := prepareTestVerify(t, testVerifyClusters)
		tamperTestTemp(t, paths.Temp, tt.mutate)

		result := runTestVerify(t, paths, params)
		assertTestVerifyFailed(t, paths, result)

		if got := failedTestChecks(result.report); !reflect.DeepEqual(got, tt.wantFailed) {
			t.Fatalf("%s: failed checks = %v, want %v", tt.name, got, tt.wantFailed)
		}
		if !strings.Contains(result.text, tt.wantDetail) {
			t.Fatalf("%s: text = %s, want detail %s", tt.name, result.text, tt.wantDetail)
		}
	}
}

func TestXlsxVerifyTruncatesTextDetails(t *testing.T) {
	t.Parallel()

	clusters := make([]testCluster, 0, 25)
	for i := 0; i < 25; i++ {
		clusters = append(clusters, testCluster{
			id: fmt.Sprintf("%d", 2001+i), domain: fmt.Sprintf("n%d.example.db", i), cloud: "0",
		})
	}
	paths, params := prepareTestVerify(t, clusters)
	tamperTestTemp(t, paths.Temp, func(lines []string) []string {
		for i := range lines {
			lines[i] = strings.Replace(lines[i], `"enabled"`, `"disabled"`, 1)
		}
		return lines
	})

	result := runTestVerify(t, paths, params)
	assertTestVerifyFailed(t, paths, result)

	if got := strings.Count(result.text, "reason: "+xlsxReasonValueMis); got != xlsxMaxTextDetails {
		t.Fatalf("text details = %d, want %d", got, xlsxMaxTextDetails)
	}
	if !strings.Contains(result.text, "... more: 5") {
		t.Fatalf("text = %s, want ... more: 5", result.text)
	}
	if got := len(testMismatches(result.report, xlsxCheckIDC5)); got != 25 {
		t.Fatalf("json C5 mismatches = %d, want 25", got)
	}
}

func TestXlsxVerifyNormalizedAndMerged(t *testing.T) {
	t.Parallel()

	run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(testDBMHeadersZh, []testCluster{
		{id: "1001", domain: "a.example.db:3306", cloud: "0", clusterType: "tendbha", status: "正常"},
		{id: "1002", domain: "b.example.db", cloud: "1", clusterType: "tendbha", status: "temporary"},
		{id: "1002", domain: "b.example.db", cloud: "1", clusterType: "tendbha", status: "temporary"},
	})}, nil)
	if run.err != nil {
		t.Fatalf("create from xlsx failed: %s", run.err)
	}

	report := readTestReport(t, run.report)
	wantNormalized := []xlsxNormalized{{Row: 2, Field: xlsxFieldClusterName, Xlsx: "a.example.db:3306",
		JSON: "a.example.db", Reason: xlsxReasonPortRemove}}
	if !reflect.DeepEqual(report.Normalized, wantNormalized) {
		t.Fatalf("normalized = %+v, want %+v", report.Normalized, wantNormalized)
	}
	wantMerged := []xlsxMerged{{Row: 4, MergedIntoRow: 3, ClusterID: 1002}}
	if !reflect.DeepEqual(report.Merged, wantMerged) {
		t.Fatalf("merged = %+v, want %+v", report.Merged, wantMerged)
	}
	for _, want := range []string{
		"row: 2, field: cluster_name, xlsx: a.example.db:3306, json: a.example.db, reason: port removed",
		"row: 4, merged_into_row: 3, cluster_id: 1002",
		"[PASS] C7 count: 3 = 2 + 1",
		"by_status: temporary: 1, 正常: 1",
	} {
		if !strings.Contains(run.text, want) {
			t.Fatalf("text = %s, want %s", run.text, want)
		}
	}
}

func TestXlsxVerifyWarnings(t *testing.T) {
	t.Parallel()

	tests := []struct {
		switchVersion string
		status        string
		wantFirst     string
		wantAbsent    string
	}{
		{switchVersion: "v2", status: "enabled", wantFirst: xlsxWarnSwitchedByV2, wantAbsent: xlsxWarnNotVisible},
		{switchVersion: "v1", status: "enabled", wantFirst: xlsxWarnNotVisible, wantAbsent: xlsxWarnSwitchedByV2},
		{switchVersion: "v2", status: "disabled", wantFirst: xlsxWarnNotVisible, wantAbsent: xlsxWarnSwitchedByV2},
		{switchVersion: "v1", status: "disabled", wantFirst: xlsxWarnNotVisible, wantAbsent: xlsxWarnSwitchedByV2},
	}

	headers := []string{"集群 ID", "主域名", "管控区域"}
	for _, tt := range tests {
		run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters(headers, []testCluster{
			{id: "1001", domain: "a.example.db", cloud: "0"},
		})}, func(opts *XlsxTemplateOptions) {
			opts.SwitchVersion = tt.switchVersion
			opts.Status = tt.status
		})
		if run.err != nil {
			t.Fatalf("%s/%s failed: %s", tt.switchVersion, tt.status, run.err)
		}

		report := readTestReport(t, run.report)
		want := []string{tt.wantFirst, xlsxWarnImportAdd}
		if !reflect.DeepEqual(report.Warnings, want) {
			t.Fatalf("%s/%s warnings = %v, want %v", tt.switchVersion, tt.status, report.Warnings, want)
		}
		textWarnings := "warnings:\n  - " + tt.wantFirst + "\n  - " + xlsxWarnImportAdd + "\n"
		if !strings.Contains(run.text, textWarnings) || strings.Contains(run.text, tt.wantAbsent) {
			t.Fatalf("%s/%s text = %s, want only %v", tt.switchVersion, tt.status, run.text, want)
		}
	}
}

func TestXlsxPathConflicts(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	input := filepath.Join(dir, testXlsxFileName)
	output := filepath.Join(dir, "whitelist.jsonl")
	tests := []struct {
		name   string
		opts   XlsxTemplateOptions
		wantOK bool
	}{
		{name: "output is input", opts: XlsxTemplateOptions{XlsxFile: input, Output: input}},
		{name: "temp is input", opts: XlsxTemplateOptions{XlsxFile: output + xlsxTempSuffix, Output: output}},
		{name: "report is input", opts: XlsxTemplateOptions{XlsxFile: input, Output: output, Report: input}},
		{name: "report is output", opts: XlsxTemplateOptions{XlsxFile: input, Output: output, Report: output}},
		{name: "report is temp", opts: XlsxTemplateOptions{XlsxFile: input, Output: output,
			Report: output + xlsxTempSuffix}},
		{name: "unclean report", opts: XlsxTemplateOptions{XlsxFile: input, Output: output,
			Report: filepath.Join(dir, "sub", "..", "whitelist.jsonl")}},
		{name: "distinct", opts: XlsxTemplateOptions{XlsxFile: input, Output: output}, wantOK: true},
	}

	for _, tt := range tests {
		_, err := resolveXlsxPaths(tt.opts)
		if tt.wantOK {
			if err != nil {
				t.Fatalf("%s: error = %s, want nil", tt.name, err)
			}
			continue
		}
		assertXlsxError(t, err, "xlsx paths conflict")
	}
}

func TestXlsxVerifyDetectsClusterIDTampering(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		mutate     func([]string) []string
		wantFailed []string
		wantC5     []xlsxMismatch
		wantDetail string
	}{
		{name: "id only", mutate: replaceTestLine(0, `"cluster_id":1001`, `"cluster_id":9998`),
			wantFailed: []string{xlsxCheckIDC3, xlsxCheckIDC4, xlsxCheckIDC5},
			wantC5: []xlsxMismatch{{Check: xlsxCheckIDC5, Row: 2, Line: 1, Field: xlsxFieldClusterID, Xlsx: "1001",
				Expected: "1001", JSON: "9998", Reason: xlsxReasonValueMis}},
			wantDetail: "row: 2, line: 1, field: cluster_id, xlsx: 1001, expected: 1001, json: 9998"},
		{name: "id and name", mutate: func(lines []string) []string {
			lines = replaceTestLine(0, `"cluster_id":1001`, `"cluster_id":9998`)(lines)
			return replaceTestLine(0, `"a.example.db"`, `"z.example.db"`)(lines)
		},
			wantFailed: []string{xlsxCheckIDC3, xlsxCheckIDC4},
			wantC5:     []xlsxMismatch{},
			wantDetail: "line: 1, cluster_id: 9998, reason: " + xlsxReasonNotSource},
		{name: "id of other cluster", mutate: replaceTestLine(0, `"cluster_id":1001`, `"cluster_id":1002`),
			wantFailed: []string{xlsxCheckIDC3, xlsxCheckIDC5, xlsxCheckIDC6},
			wantC5: []xlsxMismatch{
				{Check: xlsxCheckIDC5, Row: 3, Line: 1, Field: xlsxFieldBkCloudID, Xlsx: "0", Expected: "0", JSON: "1",
					Reason: xlsxReasonValueMis},
				{Check: xlsxCheckIDC5, Row: 3, Line: 1, Field: xlsxFieldClusterName, Xlsx: "b.example.db",
					Expected: "b.example.db", JSON: "a.example.db", Reason: xlsxReasonValueMis},
			},
			wantDetail: "line: 2, field: cluster_id, json: 1002, reason: duplicate, first line: 1"},
	}

	for _, tt := range tests {
		paths, params := prepareTestVerify(t, testVerifyClusters)
		tamperTestTemp(t, paths.Temp, tt.mutate)

		result := runTestVerify(t, paths, params)
		assertTestVerifyFailed(t, paths, result)

		if got := failedTestChecks(result.report); !reflect.DeepEqual(got, tt.wantFailed) {
			t.Fatalf("%s: failed checks = %v, want %v", tt.name, got, tt.wantFailed)
		}
		if got := testMismatches(result.report, xlsxCheckIDC5); !reflect.DeepEqual(got, tt.wantC5) {
			t.Fatalf("%s: C5 mismatches = %+v, want %+v", tt.name, got, tt.wantC5)
		}
		if !strings.Contains(result.text, tt.wantDetail) {
			t.Fatalf("%s: text = %s, want detail %s", tt.name, result.text, tt.wantDetail)
		}
	}
}

func TestXlsxReportJSONKeepsStatKeys(t *testing.T) {
	t.Parallel()

	run := runTestXlsx(t, testXlsxBook{rows: testRowsFromClusters([]string{"集群 ID", "主域名", "管控区域"},
		[]testCluster{{id: "1001", domain: "a.example.db", cloud: "0"}})}, nil)
	if run.err != nil {
		t.Fatalf("create from xlsx failed: %s", run.err)
	}

	content, err := os.ReadFile(run.report)
	if err != nil {
		t.Fatalf("read report failed: %s", err)
	}
	var raw struct {
		Stats map[string]json.RawMessage `json:"stats"`
	}
	if err := json.Unmarshal(content, &raw); err != nil {
		t.Fatalf("unmarshal report failed: %s", err)
	}

	want := map[string]string{"by_bk_cloud_id": `{"0":1}`, "by_cluster_type": "null", "by_status": "null"}
	got := make(map[string]string, len(raw.Stats))
	for key, value := range raw.Stats {
		var compact bytes.Buffer
		if err := json.Compact(&compact, value); err != nil {
			t.Fatalf("compact stats %s failed: %s", key, err)
		}
		got[key] = compact.String()
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("stats = %v, want %v", got, want)
	}
}
