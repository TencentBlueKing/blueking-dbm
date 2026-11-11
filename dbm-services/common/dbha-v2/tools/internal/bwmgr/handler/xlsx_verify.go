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
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/tools/internal/bwmgr"
)

var xlsxJSONIntegerPattern = regexp.MustCompile(`^-?\d+$`)

var xlsxStrictIntKeys = map[string]bool{
	xlsxFieldBkBizID:   true,
	xlsxFieldBkCloudID: true,
	xlsxFieldClusterID: true,
}

var xlsxStrictKeys = []string{
	xlsxFieldAction,
	xlsxFieldBkBizID,
	xlsxFieldBkCloudID,
	xlsxFieldClusterID,
	xlsxFieldClusterName,
	xlsxFieldSwitchVersion,
	xlsxFieldStatus,
}

type xlsxVerifyReport struct {
	Result             string            `json:"result"`
	GeneratedAt        string            `json:"generated_at"`
	Source             string            `json:"source"`
	Output             string            `json:"output"`
	OutputWritten      bool              `json:"output_written"`
	ExistingOutputKept bool              `json:"existing_output_kept"`
	Params             xlsxReportParams  `json:"params"`
	Counts             xlsxReportCounts  `json:"counts"`
	Checks             []xlsxCheckResult `json:"checks"`
	Stats              xlsxReportStats   `json:"stats"`
	Mismatches         []xlsxMismatch    `json:"mismatches"`
	Normalized         []xlsxNormalized  `json:"normalized"`
	Merged             []xlsxMerged      `json:"merged"`
	Warnings           []string          `json:"warnings"`
	uniqueClusterIDs   int
	uniqueClusterNames int
}

type xlsxReportParams struct {
	BkBizID       int    `json:"bk_biz_id"`
	BkBizIDFrom   string `json:"bk_biz_id_from"`
	SwitchVersion string `json:"switch_version"`
	Status        string `json:"status"`
}

type xlsxReportCounts struct {
	SourceRows       int `json:"source_rows"`
	DataRows         int `json:"data_rows"`
	EmptyRows        int `json:"empty_rows"`
	OutputLines      int `json:"output_lines"`
	MergedDuplicates int `json:"merged_duplicates"`
}

type xlsxCheckResult struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	Result string `json:"result"`
	Passed int    `json:"passed"`
	Total  int    `json:"total"`
}

type xlsxReportStats struct {
	ByBkCloudID   map[string]int `json:"by_bk_cloud_id"`
	ByClusterType map[string]int `json:"by_cluster_type"`
	ByStatus      map[string]int `json:"by_status"`
}

type xlsxMismatch struct {
	Check     string `json:"check"`
	Row       int    `json:"row,omitempty"`
	Line      int    `json:"line,omitempty"`
	ClusterID int    `json:"cluster_id,omitempty"`
	Field     string `json:"field,omitempty"`
	Xlsx      string `json:"xlsx,omitempty"`
	Expected  string `json:"expected,omitempty"`
	JSON      string `json:"json,omitempty"`
	Reason    string `json:"reason"`
}

type xlsxNormalized struct {
	Row    int    `json:"row"`
	Field  string `json:"field"`
	Xlsx   string `json:"xlsx"`
	JSON   string `json:"json"`
	Reason string `json:"reason"`
}

type xlsxMerged struct {
	Row           int `json:"row"`
	MergedIntoRow int `json:"merged_into_row"`
	ClusterID     int `json:"cluster_id"`
}

type xlsxExpected struct {
	Row           xlsxSourceRow
	Record        importAddTemplateRecord
	DomainInvalid bool
}

type xlsxMergeConflict struct {
	field    string
	xlsx     string
	expected string
}

type xlsxOutputLine struct {
	Line   int
	Text   string
	Record importRecord
	Parsed bool
	Valid  bool
}

type xlsxVerifier struct {
	params         xlsxParams
	bkBizID        int
	src            xlsxSource
	expected       []xlsxExpected
	expectedByID   map[int]int
	expectedByName map[string]int
	rowGroups      map[int]int
	conflictRows   map[int][]xlsxMergeConflict
	lines          []xlsxOutputLine
	report         *xlsxVerifyReport
}

func verifyAndFinalizeXlsxTemplate(paths xlsxPaths, params xlsxParams, out io.Writer) error {
	report, err := verifyXlsxTemplate(paths, params)
	if err != nil {
		removeXlsxTemp(paths.Temp)
		return err
	}

	if report.Result == xlsxResultPass {
		if err := os.Rename(paths.Temp, paths.Output); err != nil {
			removeXlsxTemp(paths.Temp)
			return gerrors.Newf(gerrors.Failure, errXlsxRenameFmt, paths.Output, err)
		}
		report.OutputWritten = true
	} else {
		removeXlsxTemp(paths.Temp)
		report.ExistingOutputKept = xlsxFileExists(paths.Output)
	}

	if err := writeXlsxReportJSON(paths.Report, report); err != nil {
		return err
	}

	if _, err := io.WriteString(out, renderXlsxTextReport(paths, report)); err != nil {
		return gerrors.Newf(gerrors.Failure, errWriteOutputFormat, err)
	}

	if report.Result != xlsxResultPass {
		return gerrors.Newf(gerrors.Failure, errXlsxVerifyFailedFmt, paths.Report)
	}

	return nil
}

func removeXlsxTemp(tempPath string) {
	_ = os.Remove(tempPath)
}

func xlsxFileExists(filePath string) bool {
	_, err := os.Stat(filePath)
	return err == nil
}

func verifyXlsxTemplate(paths xlsxPaths, params xlsxParams) (*xlsxVerifyReport, error) {
	src, err := readXlsxSource(paths.Input)
	if err != nil {
		return nil, err
	}

	rawLines, err := readXlsxOutputLines(paths.Temp)
	if err != nil {
		return nil, err
	}

	v := newXlsxVerifier(paths, params, src)
	v.buildExpected()
	v.checkLines(rawLines)
	v.report.Checks = []xlsxCheckResult{
		v.lineCheck(xlsxCheckIDC1, xlsxCheckImportable),
		v.lineCheck(xlsxCheckIDC2, xlsxCheckFieldSet),
		v.checkCoverage(),
		v.checkNoExtra(),
		v.checkFieldMatch(),
		v.checkUnique(),
		v.checkCount(),
	}
	v.buildStats()

	v.report.Result = xlsxResultPass
	for _, check := range v.report.Checks {
		if check.Result != xlsxResultPass {
			v.report.Result = xlsxResultFail
		}
	}

	return v.report, nil
}

func newXlsxVerifier(paths xlsxPaths, params xlsxParams, src xlsxSource) *xlsxVerifier {
	return &xlsxVerifier{
		params:         params,
		bkBizID:        verifyXlsxBkBizID(paths.Input, params),
		src:            src,
		expectedByID:   make(map[int]int, len(src.Rows)),
		expectedByName: make(map[string]int, len(src.Rows)),
		rowGroups:      make(map[int]int, len(src.Rows)),
		conflictRows:   make(map[int][]xlsxMergeConflict),
		report: &xlsxVerifyReport{
			GeneratedAt: time.Now().Format(time.RFC3339),
			Source:      paths.Input,
			Output:      paths.Output,
			Params: xlsxReportParams{
				BkBizID:       params.BkBizID,
				BkBizIDFrom:   params.BkBizIDFrom,
				SwitchVersion: params.SwitchVersion,
				Status:        params.Status,
			},
			Counts: xlsxReportCounts{
				SourceRows: src.SourceRows,
				DataRows:   len(src.Rows),
				EmptyRows:  src.EmptyRows,
			},
			Mismatches: make([]xlsxMismatch, 0),
			Normalized: make([]xlsxNormalized, 0),
			Merged:     make([]xlsxMerged, 0),
			Warnings:   xlsxWarnings(params),
		},
	}
}

func xlsxWarnings(params xlsxParams) []string {
	visible := params.SwitchVersion == string(bwmgr.SwitchVersionV2) && params.Status == string(bwmgr.StatusEnabled)
	if visible {
		return []string{xlsxWarnSwitchedByV2, xlsxWarnImportAdd}
	}

	return []string{xlsxWarnNotVisible, xlsxWarnImportAdd}
}

// buildExpected derives expected records from the source rows. Field conversion, the bk_biz_id from the file
// name, and the merge conflict check are implemented independently; only the xlsx parsing is shared.
func (v *xlsxVerifier) buildExpected() {
	for _, sourceRow := range v.src.Rows {
		rawDomain := sourceRow.Values[xlsxColDomain]
		domain, portRemoved, domainValid := verifyXlsxDomain(rawDomain)
		if !domainValid {
			domain = strings.TrimSpace(rawDomain)
		}
		if portRemoved {
			v.report.Normalized = append(v.report.Normalized, xlsxNormalized{
				Row:    sourceRow.Row,
				Field:  xlsxFieldClusterName,
				Xlsx:   strings.TrimSpace(rawDomain),
				JSON:   domain,
				Reason: xlsxReasonPortRemove,
			})
		}

		clusterID := verifyParseXlsxInt(sourceRow.Values[xlsxColClusterID])
		bkCloudID := verifyParseXlsxInt(sourceRow.Values[xlsxColBkCloudID])
		if idx, ok := v.expectedByID[clusterID]; ok {
			v.rowGroups[sourceRow.Row] = idx
			v.report.Merged = append(v.report.Merged, xlsxMerged{
				Row:           sourceRow.Row,
				MergedIntoRow: v.expected[idx].Row.Row,
				ClusterID:     clusterID,
			})
			v.recordMergeConflicts(sourceRow, idx, domain, bkCloudID)
			continue
		}

		v.expectedByID[clusterID] = len(v.expected)
		if _, ok := v.expectedByName[domain]; !ok {
			v.expectedByName[domain] = len(v.expected)
		}
		v.rowGroups[sourceRow.Row] = len(v.expected)
		v.expected = append(v.expected, xlsxExpected{
			Row: sourceRow,
			Record: importAddTemplateRecord{
				Action:        importActionAdd,
				BkBizID:       v.bkBizID,
				BkCloudID:     bkCloudID,
				ClusterID:     clusterID,
				ClusterName:   domain,
				SwitchVersion: v.params.SwitchVersion,
				Status:        v.params.Status,
			},
			DomainInvalid: !domainValid,
		})
	}
	v.report.Counts.MergedDuplicates = len(v.report.Merged)
}

// recordMergeConflicts compares a merged row with the first row of its cluster_id group using normalized values.
func (v *xlsxVerifier) recordMergeConflicts(sourceRow xlsxSourceRow, firstIdx int, domain string, bkCloudID int) {
	first := v.expected[firstIdx].Record
	if domain != first.ClusterName {
		v.conflictRows[sourceRow.Row] = append(v.conflictRows[sourceRow.Row], xlsxMergeConflict{
			field:    xlsxFieldClusterName,
			xlsx:     strings.TrimSpace(sourceRow.Values[xlsxColDomain]),
			expected: first.ClusterName,
		})
	}

	if bkCloudID != first.BkCloudID {
		v.conflictRows[sourceRow.Row] = append(v.conflictRows[sourceRow.Row], xlsxMergeConflict{
			field:    xlsxFieldBkCloudID,
			xlsx:     strings.TrimSpace(sourceRow.Values[xlsxColBkCloudID]),
			expected: strconv.Itoa(first.BkCloudID),
		})
	}
}

// verifyXlsxBkBizID derives bk_biz_id from the xlsx file name without the generation regex. The source marker
// BkBizIDFrom is trusted from the generation side; a flag value is used as is because it is not converted.
func verifyXlsxBkBizID(inputPath string, params xlsxParams) int {
	if params.BkBizIDFrom == xlsxBizFromFlag {
		return params.BkBizID
	}

	name, ok := strings.CutSuffix(filepath.Base(inputPath), xlsxVerifyFileExt)
	if !ok {
		return xlsxVerifyInvalidInt
	}

	stampStart := len(name) - xlsxVerifyStampDigits
	if stampStart > 1 && name[stampStart-1] == '_' && verifyXlsxASCIIDigits(name[stampStart:]) {
		name = name[:stampStart-1]
	}

	name, ok = strings.CutSuffix(name, xlsxVerifyNameSuffix)
	if !ok {
		return xlsxVerifyInvalidInt
	}

	closeIdx := strings.LastIndexByte(name, ')')
	if closeIdx < 0 || closeIdx == len(name)-1 {
		return xlsxVerifyInvalidInt
	}
	for i := closeIdx + 1; i < len(name); i++ {
		ch := name[i]
		if (ch < 'a' || ch > 'z') && (ch < '0' || ch > '9') && ch != '_' {
			return xlsxVerifyInvalidInt
		}
	}

	idStart := closeIdx
	for idStart > 0 && name[idStart-1] >= '0' && name[idStart-1] <= '9' {
		idStart--
	}
	if idStart == closeIdx || idStart == 0 || name[idStart-1] != '(' {
		return xlsxVerifyInvalidInt
	}

	bkBizID, err := strconv.Atoi(name[idStart:closeIdx])
	if err != nil || bkBizID <= 0 {
		return xlsxVerifyInvalidInt
	}

	return bkBizID
}

// verifyXlsxDomain strips an optional numeric port and requires the host to use only letters, digits, '.', '-' or '_'.
func verifyXlsxDomain(raw string) (domain string, portRemoved bool, valid bool) {
	var port string
	domain, port, portRemoved = strings.Cut(strings.TrimSpace(raw), ":")
	if domain == "" || (portRemoved && !verifyXlsxASCIIDigits(port)) {
		return "", false, false
	}

	for i := 0; i < len(domain); i++ {
		ch := domain[i]
		isLetter := (ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z')
		if !isLetter && (ch < '0' || ch > '9') && ch != '.' && ch != '-' && ch != '_' {
			return "", false, false
		}
	}

	return domain, portRemoved, true
}

// verifyParseXlsxInt accepts the same values as the generation side, such as "123" and "123.0", and maps
// anything else to xlsxVerifyInvalidInt.
func verifyParseXlsxInt(raw string) int {
	intPart, fracPart, hasDot := strings.Cut(strings.TrimSpace(raw), ".")
	if !verifyXlsxASCIIDigits(intPart) {
		return xlsxVerifyInvalidInt
	}

	if hasDot && (fracPart == "" || strings.Count(fracPart, "0") != len(fracPart)) {
		return xlsxVerifyInvalidInt
	}

	value, err := strconv.Atoi(intPart)
	if err != nil || value > math.MaxInt32 {
		return xlsxVerifyInvalidInt
	}

	return value
}

func verifyXlsxASCIIDigits(value string) bool {
	if value == "" {
		return false
	}

	for i := 0; i < len(value); i++ {
		if value[i] < '0' || value[i] > '9' {
			return false
		}
	}

	return true
}

func readXlsxOutputLines(filePath string) ([]xlsxOutputLine, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, errXlsxReadOutputFmt, filePath, err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 0, 64*1024), importScannerMaxCapacity)

	lines := make([]xlsxOutputLine, 0)
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		text := strings.TrimSpace(scanner.Text())
		if text == "" {
			continue
		}
		lines = append(lines, xlsxOutputLine{Line: lineNo, Text: text})
	}

	if err := scanner.Err(); err != nil {
		return nil, gerrors.Newf(gerrors.Failure, errXlsxReadOutputFmt, filePath, err)
	}

	return lines, nil
}

func (v *xlsxVerifier) checkLines(lines []xlsxOutputLine) {
	for _, line := range lines {
		record, parsed, reason := checkXlsxImportable(line)
		line.Record = record
		line.Parsed = parsed
		importable := reason == ""
		if !importable {
			v.addMismatch(xlsxMismatch{Check: xlsxCheckIDC1, Line: line.Line, Reason: reason})
		}

		field, strictReason := checkXlsxLineStrict(line.Text)
		if strictReason != "" {
			v.addMismatch(xlsxMismatch{Check: xlsxCheckIDC2, Line: line.Line, Field: field, Reason: strictReason})
		}

		line.Valid = importable && strictReason == ""
		v.lines = append(v.lines, line)
	}
}

func checkXlsxImportable(line xlsxOutputLine) (importRecord, bool, string) {
	entry, err := parseImportEntry(line.Line, line.Text)
	if err != nil {
		return importRecord{}, false, err.Error()
	}

	if err := validateImportEntry(entry); err != nil {
		return entry.Record, true, err.Error()
	}

	if entry.Record.Action != importActionAdd {
		return entry.Record, true, xlsxReasonNotAdd
	}

	return entry.Record, true, ""
}

// checkXlsxLineStrict walks JSON tokens so duplicate, null, case-folded, or unknown keys cannot be hidden.
func checkXlsxLineStrict(text string) (string, string) {
	decoder := json.NewDecoder(strings.NewReader(text))
	decoder.UseNumber()

	if tok, err := decoder.Token(); err != nil || tok != json.Delim('{') {
		return "", xlsxReasonNotObject
	}

	seen := make(map[string]bool, len(xlsxStrictKeys))
	for decoder.More() {
		keyTok, err := decoder.Token()
		if err != nil {
			return "", xlsxReasonNotObject
		}
		key, _ := keyTok.(string)

		valueTok, err := decoder.Token()
		if err != nil {
			return key, xlsxReasonNotObject
		}

		if reason := checkXlsxStrictValue(key, valueTok, seen); reason != "" {
			return key, reason
		}
		seen[key] = true
	}

	if tok, err := decoder.Token(); err != nil || tok != json.Delim('}') {
		return "", xlsxReasonNotObject
	}

	if _, err := decoder.Token(); err != io.EOF {
		return "", xlsxReasonNotObject
	}

	for _, key := range xlsxStrictKeys {
		if !seen[key] {
			return key, xlsxReasonMissingKey
		}
	}

	return "", ""
}

func checkXlsxStrictValue(key string, value json.Token, seen map[string]bool) string {
	if !isXlsxStrictKey(key) {
		return xlsxReasonUnexpKey
	}

	if seen[key] {
		return xlsxReasonDupKey
	}

	switch typed := value.(type) {
	case nil:
		return xlsxReasonNullValue
	case json.Number:
		if !xlsxStrictIntKeys[key] {
			return xlsxReasonTypeMis
		}
		if !xlsxJSONIntegerPattern.MatchString(typed.String()) {
			return xlsxReasonNonInteger
		}
	case string:
		if xlsxStrictIntKeys[key] {
			return xlsxReasonTypeMis
		}
	default:
		return xlsxReasonTypeMis
	}

	return ""
}

func isXlsxStrictKey(key string) bool {
	for _, allowed := range xlsxStrictKeys {
		if key == allowed {
			return true
		}
	}

	return false
}

func (v *xlsxVerifier) addMismatch(mismatch xlsxMismatch) {
	v.report.Mismatches = append(v.report.Mismatches, mismatch)
}

func (v *xlsxVerifier) lineCheck(id string, name string) xlsxCheckResult {
	failed := make(map[int]bool)
	for _, mismatch := range v.report.Mismatches {
		if mismatch.Check == id {
			failed[mismatch.Line] = true
		}
	}

	return newXlsxCheckResult(id, name, len(v.lines)-len(failed), len(v.lines))
}

func newXlsxCheckResult(id string, name string, passed int, total int) xlsxCheckResult {
	result := xlsxResultPass
	if passed != total {
		result = xlsxResultFail
	}

	return xlsxCheckResult{ID: id, Name: name, Result: result, Passed: passed, Total: total}
}

func (v *xlsxVerifier) validLineByClusterID() map[int]xlsxOutputLine {
	byID := make(map[int]xlsxOutputLine, len(v.lines))
	for _, line := range v.lines {
		if !line.Valid {
			continue
		}
		if _, ok := byID[line.Record.ClusterID]; !ok {
			byID[line.Record.ClusterID] = line
		}
	}

	return byID
}

func (v *xlsxVerifier) checkCoverage() xlsxCheckResult {
	validByID := v.validLineByClusterID()
	invalidIDs := make(map[int]bool)
	for _, line := range v.lines {
		if !line.Valid && line.Parsed {
			invalidIDs[line.Record.ClusterID] = true
		}
	}

	passed := 0
	for _, sourceRow := range v.src.Rows {
		expected := v.expected[v.rowGroups[sourceRow.Row]]
		conflicts := v.conflictRows[sourceRow.Row]
		_, covered := validByID[expected.Record.ClusterID]
		if covered && len(conflicts) == 0 {
			passed++
			continue
		}

		if !covered {
			reason := xlsxReasonMissing
			if invalidIDs[expected.Record.ClusterID] {
				reason = xlsxReasonNoValid
			}
			v.addMismatch(xlsxMismatch{
				Check:     xlsxCheckIDC3,
				Row:       sourceRow.Row,
				ClusterID: expected.Record.ClusterID,
				Reason:    reason,
			})
		}

		for _, conflict := range conflicts {
			v.addMismatch(xlsxMismatch{
				Check:     xlsxCheckIDC3,
				Row:       sourceRow.Row,
				ClusterID: expected.Record.ClusterID,
				Field:     conflict.field,
				Xlsx:      conflict.xlsx,
				Expected:  conflict.expected,
				Reason:    xlsxReasonMergeConfl,
			})
		}
	}

	return newXlsxCheckResult(xlsxCheckIDC3, xlsxCheckCoverage, passed, len(v.src.Rows))
}

func (v *xlsxVerifier) checkNoExtra() xlsxCheckResult {
	passed, total := 0, 0
	for _, line := range v.lines {
		if !line.Valid {
			continue
		}

		total++
		if _, ok := v.expectedByID[line.Record.ClusterID]; ok {
			passed++
			continue
		}

		v.addMismatch(xlsxMismatch{
			Check:     xlsxCheckIDC4,
			Line:      line.Line,
			ClusterID: line.Record.ClusterID,
			Reason:    xlsxReasonNotSource,
		})
	}
	v.report.Counts.OutputLines = total

	return newXlsxCheckResult(xlsxCheckIDC4, xlsxCheckNoExtra, passed, total)
}

func (v *xlsxVerifier) checkFieldMatch() xlsxCheckResult {
	passed, total := 0, 0
	for _, line := range v.lines {
		if !line.Valid {
			continue
		}

		// A line whose cluster_id is absent from the source is paired by domain so the tampered id is reported.
		idx, ok := v.expectedByID[line.Record.ClusterID]
		if !ok {
			idx, ok = v.expectedByName[line.Record.ClusterName]
		}
		if !ok {
			continue
		}

		total++
		if v.compareFields(line, v.expected[idx]) {
			passed++
		}
	}

	return newXlsxCheckResult(xlsxCheckIDC5, xlsxCheckFieldMatch, passed, total)
}

func (v *xlsxVerifier) compareFields(line xlsxOutputLine, expected xlsxExpected) bool {
	record := expected.Record
	sourceValues := expected.Row.Values
	bizValue := strconv.Itoa(record.BkBizID)
	fields := []struct {
		name     string
		xlsx     string
		expected string
		actual   string
	}{
		{xlsxFieldBkBizID, bizValue, bizValue, strconv.Itoa(line.Record.BkBizID)},
		{
			xlsxFieldClusterID,
			strings.TrimSpace(sourceValues[xlsxColClusterID]),
			strconv.Itoa(record.ClusterID),
			strconv.Itoa(line.Record.ClusterID),
		},
		{
			xlsxFieldBkCloudID,
			strings.TrimSpace(sourceValues[xlsxColBkCloudID]),
			strconv.Itoa(record.BkCloudID),
			strconv.Itoa(line.Record.BkCloudID),
		},
		{
			xlsxFieldClusterName,
			strings.TrimSpace(sourceValues[xlsxColDomain]),
			record.ClusterName,
			line.Record.ClusterName,
		},
		{xlsxFieldSwitchVersion, record.SwitchVersion, record.SwitchVersion, line.Record.SwitchVersion},
		{xlsxFieldStatus, record.Status, record.Status, line.Record.Status},
	}

	matched := true
	if expected.DomainInvalid {
		matched = false
		v.addMismatch(xlsxMismatch{
			Check:  xlsxCheckIDC5,
			Row:    expected.Row.Row,
			Line:   line.Line,
			Field:  xlsxFieldClusterName,
			Xlsx:   strings.TrimSpace(sourceValues[xlsxColDomain]),
			JSON:   line.Record.ClusterName,
			Reason: xlsxReasonSrcDomainBad,
		})
	}

	for _, field := range fields {
		if field.expected == field.actual || (expected.DomainInvalid && field.name == xlsxFieldClusterName) {
			continue
		}

		matched = false
		v.addMismatch(xlsxMismatch{
			Check:    xlsxCheckIDC5,
			Row:      expected.Row.Row,
			Line:     line.Line,
			Field:    field.name,
			Xlsx:     field.xlsx,
			Expected: field.expected,
			JSON:     field.actual,
			Reason:   xlsxReasonValueMis,
		})
	}

	return matched
}

func (v *xlsxVerifier) checkUnique() xlsxCheckResult {
	firstByID := make(map[int]int)
	firstByName := make(map[string]int)
	passed, total := 0, 0

	for _, line := range v.lines {
		if !line.Valid {
			continue
		}

		total++
		unique := true
		if first, ok := firstByID[line.Record.ClusterID]; ok {
			unique = false
			v.addUniqueMismatch(line, xlsxFieldClusterID, strconv.Itoa(line.Record.ClusterID), first)
		} else {
			firstByID[line.Record.ClusterID] = line.Line
		}

		if first, ok := firstByName[line.Record.ClusterName]; ok {
			unique = false
			v.addUniqueMismatch(line, xlsxFieldClusterName, line.Record.ClusterName, first)
		} else {
			firstByName[line.Record.ClusterName] = line.Line
		}

		if unique {
			passed++
		}
	}
	v.report.uniqueClusterIDs = len(firstByID)
	v.report.uniqueClusterNames = len(firstByName)

	return newXlsxCheckResult(xlsxCheckIDC6, xlsxCheckUnique, passed, total)
}

func (v *xlsxVerifier) addUniqueMismatch(line xlsxOutputLine, field string, value string, firstLine int) {
	v.addMismatch(xlsxMismatch{
		Check:  xlsxCheckIDC6,
		Line:   line.Line,
		Field:  field,
		JSON:   value,
		Reason: fmt.Sprintf(xlsxReasonDupFmt, firstLine),
	})
}

func (v *xlsxVerifier) checkCount() xlsxCheckResult {
	counts := v.report.Counts
	if counts.DataRows == counts.OutputLines+counts.MergedDuplicates {
		return newXlsxCheckResult(xlsxCheckIDC7, xlsxCheckCount, 1, 1)
	}

	v.addMismatch(xlsxMismatch{
		Check:    xlsxCheckIDC7,
		Expected: strconv.Itoa(counts.DataRows),
		JSON:     strconv.Itoa(counts.OutputLines + counts.MergedDuplicates),
		Reason:   xlsxReasonCountMis,
	})

	return newXlsxCheckResult(xlsxCheckIDC7, xlsxCheckCount, 0, 1)
}

func (v *xlsxVerifier) buildStats() {
	stats := xlsxReportStats{ByBkCloudID: make(map[string]int)}
	if v.src.HasColumn[xlsxColClusterType] {
		stats.ByClusterType = make(map[string]int)
	}
	if v.src.HasColumn[xlsxColStatus] {
		stats.ByStatus = make(map[string]int)
	}

	for _, expected := range v.expected {
		stats.ByBkCloudID[strconv.Itoa(expected.Record.BkCloudID)]++
		if stats.ByClusterType != nil {
			stats.ByClusterType[xlsxStatKey(expected.Row.Values[xlsxColClusterType])]++
		}
		if stats.ByStatus != nil {
			stats.ByStatus[xlsxStatKey(expected.Row.Values[xlsxColStatus])]++
		}
	}
	v.report.Stats = stats
}

func xlsxStatKey(raw string) string {
	value := strings.TrimSpace(raw)
	if value == "" {
		return xlsxEmptyStatKey
	}

	return value
}

func writeXlsxReportJSON(reportPath string, report *xlsxVerifyReport) error {
	content, err := json.MarshalIndent(report, jsonIndentPrefix, jsonIndentValue)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, errFormatOutputFormat, err)
	}
	content = append(content, '\n')

	if err := os.WriteFile(reportPath, content, 0o644); err != nil {
		return gerrors.Newf(gerrors.Failure, errXlsxWriteReportFmt, reportPath, err)
	}

	return nil
}

func renderXlsxTextReport(paths xlsxPaths, report *xlsxVerifyReport) string {
	var builder strings.Builder
	builder.WriteString(msgXlsxReportTitle)
	fmt.Fprintf(&builder, msgXlsxSourceFmt, paths.Input)
	switch {
	case report.OutputWritten:
		fmt.Fprintf(&builder, msgXlsxOutputFmt, paths.Output)
	case report.ExistingOutputKept:
		fmt.Fprintf(&builder, msgXlsxOutputKeptFmt, paths.Output)
	default:
		fmt.Fprintf(&builder, msgXlsxOutputNotWritten, paths.Output)
	}
	fmt.Fprintf(&builder, msgXlsxReportPathFmt, paths.Report)
	fmt.Fprintf(&builder, msgXlsxBizFmt, report.Params.BkBizID, report.Params.BkBizIDFrom)
	fmt.Fprintf(&builder, msgXlsxParamsFmt, report.Params.SwitchVersion, report.Params.Status)
	counts := report.Counts
	fmt.Fprintf(&builder, msgXlsxRowsFmt, counts.SourceRows, counts.DataRows, counts.EmptyRows)
	fmt.Fprintf(&builder, msgXlsxLinesFmt, counts.OutputLines, counts.MergedDuplicates)

	builder.WriteString(msgXlsxChecksTitle)
	for _, check := range report.Checks {
		renderXlsxCheck(&builder, report, check)
		renderXlsxCheckDetails(&builder, report.Mismatches, check.ID)
	}

	renderXlsxStats(&builder, report.Stats)
	renderXlsxNormalizedAndMerged(&builder, report)

	builder.WriteString(msgXlsxWarningsTitle)
	for _, warning := range report.Warnings {
		fmt.Fprintf(&builder, msgXlsxWarningItemFmt, warning)
	}
	fmt.Fprintf(&builder, msgXlsxResultFmt, report.Result)

	return builder.String()
}

func renderXlsxCheck(builder *strings.Builder, report *xlsxVerifyReport, check xlsxCheckResult) {
	counts := report.Counts
	switch check.ID {
	case xlsxCheckIDC6:
		fmt.Fprintf(builder, msgXlsxCheckUniqueFmt, check.Result, check.ID, check.Name,
			report.uniqueClusterIDs, report.uniqueClusterNames)
	case xlsxCheckIDC7:
		format := msgXlsxCheckCountPassFmt
		if check.Result != xlsxResultPass {
			format = msgXlsxCheckCountFailFmt
		}
		fmt.Fprintf(builder, format, check.Result, check.ID, check.Name,
			counts.DataRows, counts.OutputLines, counts.MergedDuplicates)
	default:
		fmt.Fprintf(builder, msgXlsxCheckFmt, check.Result, check.ID, check.Name, check.Passed, check.Total)
	}
}

func renderXlsxCheckDetails(builder *strings.Builder, mismatches []xlsxMismatch, checkID string) {
	shown, hidden := 0, 0
	for _, mismatch := range mismatches {
		if mismatch.Check != checkID {
			continue
		}

		if shown >= xlsxMaxTextDetails {
			hidden++
			continue
		}

		shown++
		fmt.Fprintf(builder, msgXlsxDetailFmt, formatXlsxMismatch(mismatch))
	}

	if hidden > 0 {
		fmt.Fprintf(builder, msgXlsxMoreFmt, hidden)
	}
}

func formatXlsxMismatch(mismatch xlsxMismatch) string {
	parts := make([]string, 0, 8)
	addInt := func(name string, value int) {
		if value != 0 {
			parts = append(parts, fmt.Sprintf(msgXlsxDetailPairFmt, name, strconv.Itoa(value)))
		}
	}
	addString := func(name string, value string) {
		if value != "" {
			parts = append(parts, fmt.Sprintf(msgXlsxDetailPairFmt, name, value))
		}
	}

	addInt(msgXlsxDetailRow, mismatch.Row)
	addInt(msgXlsxDetailLine, mismatch.Line)
	addInt(msgXlsxDetailClusterID, mismatch.ClusterID)
	addString(msgXlsxDetailField, mismatch.Field)
	addString(msgXlsxDetailXlsx, mismatch.Xlsx)
	addString(msgXlsxDetailExpected, mismatch.Expected)
	addString(msgXlsxDetailJSON, mismatch.JSON)
	addString(msgXlsxDetailReason, mismatch.Reason)

	return strings.Join(parts, xlsxListSeparator)
}

func renderXlsxStats(builder *strings.Builder, stats xlsxReportStats) {
	fmt.Fprintf(builder, msgXlsxStatFmt, msgXlsxStatByCloud, formatXlsxStat(stats.ByBkCloudID, true))
	if stats.ByClusterType != nil {
		fmt.Fprintf(builder, msgXlsxStatFmt, msgXlsxStatByType, formatXlsxStat(stats.ByClusterType, false))
	}
	if stats.ByStatus != nil {
		fmt.Fprintf(builder, msgXlsxStatFmt, msgXlsxStatByStatus, formatXlsxStat(stats.ByStatus, false))
	}
}

func formatXlsxStat(stat map[string]int, numericKeys bool) string {
	keys := make([]string, 0, len(stat))
	for key := range stat {
		keys = append(keys, key)
	}

	sort.Slice(keys, func(i, j int) bool {
		if numericKeys {
			left, _ := strconv.Atoi(keys[i])
			right, _ := strconv.Atoi(keys[j])
			return left < right
		}
		return keys[i] < keys[j]
	})

	parts := make([]string, 0, len(keys))
	for _, key := range keys {
		parts = append(parts, fmt.Sprintf(msgXlsxStatPairFmt, key, stat[key]))
	}

	return strings.Join(parts, xlsxListSeparator)
}

func renderXlsxNormalizedAndMerged(builder *strings.Builder, report *xlsxVerifyReport) {
	fmt.Fprintf(builder, msgXlsxNormalizedFmt, len(report.Normalized))
	for _, item := range report.Normalized {
		fmt.Fprintf(builder, msgXlsxNormalizedItemFmt, item.Row, item.Field, item.Xlsx, item.JSON, item.Reason)
	}

	if len(report.Merged) == 0 {
		return
	}

	builder.WriteString(msgXlsxMergedTitle)
	for _, item := range report.Merged {
		fmt.Fprintf(builder, msgXlsxMergedItemFmt, item.Row, item.MergedIntoRow, item.ClusterID)
	}
}
