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
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/tools/internal/bwmgr"
)

type recordingBlackWhiteListService struct {
	items          []bwmgr.BlackWhiteListItem
	getRequests    []bwmgr.GetBlackWhiteListRequest
	insertRequests []bwmgr.InsertBlackWhiteListRequest
	updateRequests []bwmgr.UpdateBlackWhiteListRequest
}

func (s *recordingBlackWhiteListService) GetBlackWhiteList(
	_ int,
	req *bwmgr.GetBlackWhiteListRequest,
) ([]bwmgr.BlackWhiteListItem, error) {
	if req == nil {
		return s.items, nil
	}

	s.getRequests = append(s.getRequests, *req)
	matched := make([]bwmgr.BlackWhiteListItem, 0)
	for _, item := range s.items {
		if req.BkBizID != nil && item.BkBizID != *req.BkBizID {
			continue
		}
		if req.BkCloudID != nil && item.BkCloudID != *req.BkCloudID {
			continue
		}
		if req.ClusterID != nil && item.ClusterID != *req.ClusterID {
			continue
		}
		matched = append(matched, item)
	}

	return matched, nil
}

func (s *recordingBlackWhiteListService) InsertBlackWhiteList(
	_ int,
	req bwmgr.InsertBlackWhiteListRequest,
) (uint, error) {
	s.insertRequests = append(s.insertRequests, req)
	return uint(len(s.insertRequests)), nil
}

func (s *recordingBlackWhiteListService) UpdateBlackWhiteList(
	_ int,
	req bwmgr.UpdateBlackWhiteListRequest,
) (int, error) {
	s.updateRequests = append(s.updateRequests, req)
	return 1, nil
}

func (s *recordingBlackWhiteListService) DeleteBlackWhiteList(
	_ int,
	_ bwmgr.DeleteBlackWhiteListRequest,
) (int, error) {
	return 0, nil
}

var testAcceptanceClusters = []testCluster{
	{id: "1001", domain: "a.example.db:3306", cloud: "0", clusterType: "tendbha", status: "正常"},
	{id: "1002", domain: "b.example.db", cloud: "0", clusterType: "tendbha", status: "正常"},
	{id: "1003", domain: "c.example.db", cloud: "0", clusterType: "tendbha", status: "正常"},
	{},
	{id: "1004", domain: "d.example.db", cloud: "1", clusterType: "tendbha", status: "正常"},
	{id: "1005", domain: "e.example.db", cloud: "0", clusterType: "tendbha", status: "正常"},
	{id: "1006", domain: "f.example.db", cloud: "1", clusterType: "tendbha", status: "正常"},
	{id: "1003", domain: "c.example.db", cloud: "0", clusterType: "tendbha", status: "正常"},
	{},
	{id: "1007", domain: "g.example.db", cloud: "0", clusterType: "tendbha", status: "temporary"},
	{id: "1008", domain: "h.example.db", cloud: "0", clusterType: "tendbha", status: "正常"},
	{id: "1009", domain: "i.example.db", cloud: "0", clusterType: "tendbha", status: "正常"},
}

var testAcceptanceExpected = []importAddTemplateRecord{
	testRecord(1001, "a.example.db", 0),
	testRecord(1002, "b.example.db", 0),
	testRecord(1003, "c.example.db", 0),
	testRecord(1004, "d.example.db", 1),
	testRecord(1005, "e.example.db", 0),
	testRecord(1006, "f.example.db", 1),
	testRecord(1007, "g.example.db", 0),
	testRecord(1008, "h.example.db", 0),
	testRecord(1009, "i.example.db", 0),
}

func testAcceptanceBook(headers []string, normalStatus string) testXlsxBook {
	rows := []testXlsxRow{testHeaderRow(headers)}
	for _, cluster := range testAcceptanceClusters {
		if cluster.id == "" {
			rows = append(rows, testXlsxRow{})
			continue
		}
		if cluster.status == "正常" {
			cluster.status = normalStatus
		}
		rows = append(rows, testClusterRow(headers, cluster))
	}

	return testXlsxBook{rows: rows}
}

func runTestAcceptanceE1(t *testing.T) testXlsxRun {
	t.Helper()

	run := runTestXlsx(t, testAcceptanceBook(testDBMHeadersZh, "正常"), nil)
	if run.err != nil {
		t.Fatalf("E1 create from xlsx failed: %s, report: %s", run.err, run.text)
	}

	return run
}

func TestXlsxAcceptanceE1Generate(t *testing.T) {
	t.Parallel()

	run := runTestAcceptanceE1(t)
	t.Logf("E1 text report:\n%s", run.text)

	if got := readTestRecords(t, run.output); !reflect.DeepEqual(got, testAcceptanceExpected) {
		t.Fatalf("records = %+v, want %+v", got, testAcceptanceExpected)
	}

	report := readTestReport(t, run.report)
	wantCounts := xlsxReportCounts{SourceRows: 12, DataRows: 10, EmptyRows: 2, OutputLines: 9, MergedDuplicates: 1}
	if report.Result != xlsxResultPass || report.Counts != wantCounts {
		t.Fatalf("result/counts = %s/%+v, want PASS/%+v", report.Result, report.Counts, wantCounts)
	}
	if len(report.Normalized) != 1 || report.Normalized[0].Row != 2 {
		t.Fatalf("normalized = %+v, want row 2", report.Normalized)
	}
	if !reflect.DeepEqual(report.Merged, []xlsxMerged{{Row: 9, MergedIntoRow: 4, ClusterID: 1003}}) {
		t.Fatalf("merged = %+v, want row 9 into row 4", report.Merged)
	}

	wantStats := xlsxReportStats{
		ByBkCloudID:   map[string]int{"0": 7, "1": 2},
		ByClusterType: map[string]int{"tendbha": 9},
		ByStatus:      map[string]int{"正常": 8, "temporary": 1},
	}
	if !reflect.DeepEqual(report.Stats, wantStats) {
		t.Fatalf("stats = %+v, want %+v", report.Stats, wantStats)
	}
	for _, want := range []string{
		"bk_biz_id: 591, from: filename",
		"source_rows: 12, data_rows: 10, empty_rows: 2",
		"output_lines: 9, merged_duplicates: 1",
		"by_bk_cloud_id: 0: 7, 1: 2",
		"by_cluster_type: tendbha: 9",
		"by_status: temporary: 1, 正常: 8",
		"[PASS] C6 unique: cluster_id 9, cluster_name 9",
		"[PASS] C7 count: 10 = 9 + 1",
		"result: PASS",
	} {
		if !strings.Contains(run.text, want) {
			t.Fatalf("text = %s, want %s", run.text, want)
		}
	}
}

func TestXlsxAcceptanceE2ImportInsert(t *testing.T) {
	t.Parallel()

	run := runTestAcceptanceE1(t)
	service := &recordingBlackWhiteListService{}
	if err := NewHandlerWithService(0, service).Import(ImportOptions{File: run.output}); err != nil {
		t.Fatalf("import failed: %s", err)
	}

	if len(service.insertRequests) != len(testAcceptanceExpected) || len(service.updateRequests) != 0 {
		t.Fatalf("insert/update = %d/%d, want 9/0", len(service.insertRequests), len(service.updateRequests))
	}
	for i, req := range service.insertRequests {
		want := testAcceptanceExpected[i]
		got := importAddTemplateRecord{
			Action:        importActionAdd,
			BkBizID:       req.BkBizID,
			BkCloudID:     req.BkCloudID,
			ClusterID:     req.ClusterID,
			ClusterName:   req.ClusterName,
			SwitchVersion: string(req.SwitchVersion),
			Status:        string(req.Status),
		}
		if got != want {
			t.Fatalf("insert %d = %+v, want %+v", i, got, want)
		}
	}
}

func TestXlsxAcceptanceE3ImportUpsert(t *testing.T) {
	t.Parallel()

	run := runTestAcceptanceE1(t)
	service := &recordingBlackWhiteListService{items: []bwmgr.BlackWhiteListItem{
		{ID: 11, BkBizID: 591, BkCloudID: 0, ClusterID: 1001, ClusterName: "a.example.db"},
		{ID: 12, BkBizID: 591, BkCloudID: 0, ClusterID: 1002, ClusterName: "b.example.db"},
		{ID: 13, BkBizID: 591, BkCloudID: 0, ClusterID: 1003, ClusterName: "c.example.db"},
		{ID: 14, BkBizID: 591, BkCloudID: 0, ClusterID: 1004, ClusterName: "d.example.db"},
	}}
	err := NewHandlerWithService(0, service).Import(ImportOptions{File: run.output, Upsert: true, Yes: true})
	if err != nil {
		t.Fatalf("import failed: %s", err)
	}

	if len(service.updateRequests) != 3 || len(service.insertRequests) != 6 {
		t.Fatalf("update/insert = %d/%d, want 3/6", len(service.updateRequests), len(service.insertRequests))
	}
	for i, req := range service.updateRequests {
		wantID := uint(11 + i)
		if req.QueryArgs.ID == nil || *req.QueryArgs.ID != wantID {
			t.Fatalf("update %d query id = %v, want %d", i, req.QueryArgs.ID, wantID)
		}
	}
	for _, req := range service.insertRequests {
		if req.ClusterID == 1004 && req.BkCloudID != 1 {
			t.Fatalf("insert 1004 cloud = %d, want 1", req.BkCloudID)
		}
	}
}

func TestXlsxAcceptanceE4TamperedTemp(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	opts := newTestXlsxOptions(dir, testXlsxFileName)
	writeTestXlsx(t, opts.XlsxFile, testAcceptanceBook(testDBMHeadersZh, "正常"))
	paths, params := mustTestXlsxTemp(t, opts)

	tamperTestTemp(t, paths.Temp, func(lines []string) []string {
		lines[0] = strings.Replace(lines[0], `"bk_cloud_id":0`, `"bk_cloud_id":1`, 1)
		lines[1] = strings.Replace(lines[1], `"b.example.db"`, `"bb.example.db"`, 1)
		lines[3] = strings.Replace(lines[3], `"bk_cloud_id":1`, `"bk_cloud_id":1,"bk_cloud_id":0`, 1)
		lines = append(lines[:2], lines[3:]...)
		return append(lines, strings.Replace(lines[0], "1001", "1099", 1))
	})

	var out bytes.Buffer
	err := verifyAndFinalizeXlsxTemplate(paths, params, &out)
	assertXlsxError(t, err, fmt.Sprintf(errXlsxVerifyFailedFmt, paths.Report))
	t.Logf("E4 text report:\n%s", out.String())

	for _, want := range []string{
		"row: 2, line: 1, field: bk_cloud_id, xlsx: 0, expected: 0, json: 1, reason: value mismatch",
		"row: 3, line: 2, field: cluster_name, xlsx: b.example.db, expected: b.example.db, json: bb.example.db",
		"row: 4, cluster_id: 1003, reason: missing in output",
		"line: 3, field: bk_cloud_id, reason: duplicate key",
		"line: 9, cluster_id: 1099, reason: not in source",
		"result: FAIL",
	} {
		if !strings.Contains(out.String(), want) {
			t.Fatalf("text = %s, want %s", out.String(), want)
		}
	}
	if _, err := os.Stat(paths.Output); !os.IsNotExist(err) {
		t.Fatalf("output exists = %v, want not written", err)
	}
}

func mustTestXlsxTemp(t *testing.T, opts XlsxTemplateOptions) (xlsxPaths, xlsxParams) {
	t.Helper()

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

func TestXlsxAcceptanceE5FileNames(t *testing.T) {
	t.Parallel()

	book := testAcceptanceBook(testDBMHeadersZh, "正常")
	plain := runTestXlsx(t, book, func(opts *XlsxTemplateOptions) {
		opts.XlsxFile = filepath.Join(filepath.Dir(opts.XlsxFile), "mapleleaf(591)mysql_cluster.xlsx")
	})
	if plain.err != nil {
		t.Fatalf("plain file name failed: %s", plain.err)
	}
	if report := readTestReport(t, plain.report); report.Params.BkBizID != 591 {
		t.Fatalf("bk_biz_id = %d, want 591", report.Params.BkBizID)
	}

	suffixed := runTestXlsx(t, book, func(opts *XlsxTemplateOptions) {
		opts.XlsxFile = filepath.Join(
			filepath.Dir(opts.XlsxFile), "mapleleaf(591)mysql_cluster_20261104101251 (1).xlsx",
		)
	})
	assertXlsxError(t, suffixed.err, "--xlsx-bk-biz-id")
	assertNoXlsxOutputs(t, suffixed)
}

func TestXlsxAcceptanceE7EnglishHeaders(t *testing.T) {
	t.Parallel()

	zh := runTestAcceptanceE1(t)
	en := runTestXlsx(t, testAcceptanceBook(testDBMHeadersEn, "normal"), nil)
	if en.err != nil {
		t.Fatalf("english headers failed: %s", en.err)
	}

	zhContent, err := os.ReadFile(zh.output)
	if err != nil {
		t.Fatalf("read zh output failed: %s", err)
	}
	enContent, err := os.ReadFile(en.output)
	if err != nil {
		t.Fatalf("read en output failed: %s", err)
	}
	if !bytes.Equal(zhContent, enContent) {
		t.Fatalf("english output = %s, want %s", enContent, zhContent)
	}

	report := readTestReport(t, en.report)
	if report.Result != xlsxResultPass ||
		!reflect.DeepEqual(report.Stats.ByStatus, map[string]int{"normal": 8, "temporary": 1}) {
		t.Fatalf("result/by_status = %s/%v, want PASS/normal 8 temporary 1", report.Result, report.Stats.ByStatus)
	}
}

func TestXlsxAcceptanceE8ExistingOutputKept(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	opts := newTestXlsxOptions(dir, testXlsxFileName)
	writeTestXlsx(t, opts.XlsxFile, testAcceptanceBook(testDBMHeadersZh, "正常"))
	oldContent := []byte("old\n")
	if err := os.WriteFile(opts.Output, oldContent, 0o644); err != nil {
		t.Fatalf("write old output failed: %s", err)
	}
	oldTime := time.Now().Add(-time.Hour).Truncate(time.Second)
	if err := os.Chtimes(opts.Output, oldTime, oldTime); err != nil {
		t.Fatalf("set old output time failed: %s", err)
	}

	paths, params := mustTestXlsxTemp(t, opts)
	tamperTestTemp(t, paths.Temp, replaceTestLine(0, `"bk_cloud_id":0`, `"bk_cloud_id":1`))

	var out bytes.Buffer
	err := verifyAndFinalizeXlsxTemplate(paths, params, &out)
	assertXlsxError(t, err, fmt.Sprintf(errXlsxVerifyFailedFmt, paths.Report))

	content, err := os.ReadFile(paths.Output)
	if err != nil || !bytes.Equal(content, oldContent) {
		t.Fatalf("old output = %q/%v, want %q", content, err, oldContent)
	}
	info, err := os.Stat(paths.Output)
	if err != nil || !info.ModTime().Equal(oldTime) {
		t.Fatalf("old output mtime = %v/%v, want %v", info, err, oldTime)
	}

	report := readTestReport(t, paths.Report)
	if report.OutputWritten || !report.ExistingOutputKept {
		t.Fatalf("output written/kept = %v/%v, want false/true", report.OutputWritten, report.ExistingOutputKept)
	}
	if !strings.Contains(out.String(), fmt.Sprintf(msgXlsxOutputKeptFmt, paths.Output)) {
		t.Fatalf("text = %s, want existing file kept", out.String())
	}
}

func TestXlsxAcceptanceE9HiddenRows(t *testing.T) {
	t.Parallel()

	book := testAcceptanceBook(testDBMHeadersZh, "正常")
	book.rows[2].hidden = xlsxBoolOne
	book.rows[6].hidden = xlsxBoolTrue

	run := runTestXlsx(t, book, nil)
	assertXlsxError(t, run.err, fmt.Sprintf(errXlsxHiddenRowsFmt, "3, 7"))
	assertNoXlsxOutputs(t, run)
}
