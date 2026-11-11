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
	"io"
	"math"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

const (
	xlsxColClusterID = iota
	xlsxColDomain
	xlsxColBkCloudID
	xlsxColClusterType
	xlsxColStatus
	xlsxColumnCount
)

type xlsxColumnSpec struct {
	aliases  []string
	required bool
}

var xlsxColumnSpecs = [xlsxColumnCount]xlsxColumnSpec{
	xlsxColClusterID:   {aliases: []string{xlsxHeaderClusterIDZh, xlsxHeaderClusterIDEn}, required: true},
	xlsxColDomain:      {aliases: []string{xlsxHeaderDomainZh, xlsxHeaderDomainEn}, required: true},
	xlsxColBkCloudID:   {aliases: []string{xlsxHeaderBkCloudIDZh, xlsxHeaderBkCloudIDEn}, required: true},
	xlsxColClusterType: {aliases: []string{xlsxHeaderClusterTypeZh, xlsxHeaderClusterTypeEn}},
	xlsxColStatus:      {aliases: []string{xlsxHeaderStatusZh, xlsxHeaderStatusEn}},
}

var (
	xlsxBizFileNamePattern = regexp.MustCompile(`\((\d+)\)[a-z0-9_]+_cluster(?:_\d{14})?\.xlsx$`)
	xlsxIntegerPattern     = regexp.MustCompile(`^(\d+)(?:\.0+)?$`)
)

type xlsxSourceRow struct {
	Row    int
	Values [xlsxColumnCount]string
}

type xlsxSource struct {
	Rows       []xlsxSourceRow
	SourceRows int
	EmptyRows  int
	HasColumn  [xlsxColumnCount]bool
}

type xlsxParams struct {
	BkBizID       int
	BkBizIDFrom   string
	SwitchVersion string
	Status        string
}

type xlsxPaths struct {
	Input  string
	Output string
	Temp   string
	Report string
}

type xlsxKeptRecord struct {
	row    int
	record importAddTemplateRecord
}

// CreateImportTemplateFromXlsx converts a DBM cluster xlsx export into an add-only import file.
func CreateImportTemplateFromXlsx(opts XlsxTemplateOptions) error {
	paths, err := resolveXlsxPaths(opts)
	if err != nil {
		return err
	}

	params, err := resolveXlsxParams(opts)
	if err != nil {
		return err
	}

	src, err := readXlsxSource(paths.Input)
	if err != nil {
		return err
	}

	records, err := buildXlsxRecords(src, params)
	if err != nil {
		return err
	}

	if err := writeXlsxTemplateTemp(paths.Temp, records); err != nil {
		return err
	}

	out := opts.Out
	if out == nil {
		out = os.Stdout
	}

	return verifyAndFinalizeXlsxTemplate(paths, params, out)
}

// ValidateImportTemplateFlags checks that only one import template mode is selected.
func ValidateImportTemplateFlags(createTemplate, createTemplateFromList, createTemplateFromXlsx string) error {
	if createTemplate != "" && createTemplateFromList != "" {
		return gerrors.Newf(gerrors.InvalidParameter, errImportTemplateMutualExclusive)
	}

	if createTemplateFromXlsx != "" && (createTemplate != "" || createTemplateFromList != "") {
		return gerrors.Newf(gerrors.InvalidParameter, errXlsxTemplateMutualExclusive)
	}

	return nil
}

func resolveXlsxPaths(opts XlsxTemplateOptions) (xlsxPaths, error) {
	if opts.Output == "" {
		return xlsxPaths{}, gerrors.Newf(gerrors.InvalidParameter, errXlsxOutputRequired)
	}

	if opts.XlsxFile == "" {
		return xlsxPaths{}, gerrors.Newf(gerrors.InvalidParameter, errXlsxFileRequired)
	}

	paths := xlsxPaths{
		Input:  opts.XlsxFile,
		Output: opts.Output,
		Temp:   opts.Output + xlsxTempSuffix,
		Report: opts.Report,
	}
	if paths.Report == "" {
		paths.Report = opts.Output + xlsxReportSuffix
	}

	seen := make(map[string]struct{}, 4)
	for _, candidate := range []string{paths.Input, paths.Output, paths.Temp, paths.Report} {
		absPath, err := filepath.Abs(candidate)
		if err != nil {
			return xlsxPaths{}, gerrors.Newf(gerrors.InvalidParameter, errXlsxResolvePathFmt, candidate, err)
		}

		absPath = filepath.Clean(absPath)
		if _, ok := seen[absPath]; ok {
			return xlsxPaths{}, gerrors.Newf(gerrors.InvalidParameter, errXlsxPathConflictFmt, candidate)
		}
		seen[absPath] = struct{}{}
	}

	return paths, nil
}

func resolveXlsxParams(opts XlsxTemplateOptions) (xlsxParams, error) {
	bkBizID, from, err := resolveXlsxBkBizID(opts)
	if err != nil {
		return xlsxParams{}, err
	}

	if opts.SwitchVersion == "" {
		return xlsxParams{}, gerrors.Newf(gerrors.InvalidParameter, errXlsxSwitchVersionNeeded)
	}
	if _, err := parseSwitchVersion(opts.SwitchVersion); err != nil {
		return xlsxParams{}, err
	}

	if opts.Status == "" {
		return xlsxParams{}, gerrors.Newf(gerrors.InvalidParameter, errXlsxStatusNeeded)
	}
	if _, err := parseStatus(opts.Status); err != nil {
		return xlsxParams{}, err
	}

	return xlsxParams{
		BkBizID:       bkBizID,
		BkBizIDFrom:   from,
		SwitchVersion: opts.SwitchVersion,
		Status:        opts.Status,
	}, nil
}

func resolveXlsxBkBizID(opts XlsxTemplateOptions) (int, string, error) {
	if opts.BkBizIDSet {
		if opts.BkBizID <= 0 {
			return 0, "", gerrors.Newf(gerrors.InvalidParameter, errXlsxBkBizIDInvalid)
		}

		return opts.BkBizID, xlsxBizFromFlag, nil
	}

	name := filepath.Base(opts.XlsxFile)
	matches := xlsxBizFileNamePattern.FindStringSubmatch(name)
	if matches == nil {
		return 0, "", gerrors.Newf(gerrors.InvalidParameter, errXlsxBkBizIDFromNameFmt, name)
	}

	bkBizID, err := strconv.Atoi(matches[1])
	if err != nil || bkBizID <= 0 {
		return 0, "", gerrors.Newf(gerrors.InvalidParameter, errXlsxBkBizIDFromNameFmt, name)
	}

	return bkBizID, xlsxBizFromFilename, nil
}

func readXlsxSource(filePath string) (xlsxSource, error) {
	rows, err := readXlsxRows(filePath)
	if err != nil {
		return xlsxSource{}, err
	}

	if len(rows) == 0 {
		return xlsxSource{}, gerrors.Newf(gerrors.InvalidParameter, errXlsxHeaderRequired)
	}

	columns, err := mapXlsxHeader(rows[0])
	if err != nil {
		return xlsxSource{}, err
	}

	// Hidden rows must be rejected before data rows are parsed so their cell type errors cannot mask them.
	if err := checkXlsxHiddenRows(rows); err != nil {
		return xlsxSource{}, err
	}

	src := xlsxSource{}
	for i, col := range columns {
		src.HasColumn[i] = col >= 0
	}

	for _, row := range rows[1:] {
		src.SourceRows++
		if isXlsxRowEmpty(row) {
			src.EmptyRows++
			continue
		}

		sourceRow, err := extractXlsxSourceRow(row, columns)
		if err != nil {
			return xlsxSource{}, err
		}
		src.Rows = append(src.Rows, sourceRow)
	}

	if len(src.Rows) == 0 {
		return xlsxSource{}, gerrors.Newf(gerrors.InvalidParameter, errXlsxNoDataRows)
	}

	return src, nil
}

func checkXlsxHiddenRows(rows []xlsxRow) error {
	hidden := make([]string, 0)
	for _, row := range rows {
		if row.Hidden && !isXlsxRowEmpty(row) {
			hidden = append(hidden, strconv.Itoa(row.Num))
		}
	}

	if len(hidden) > 0 {
		return gerrors.Newf(gerrors.InvalidParameter, errXlsxHiddenRowsFmt, strings.Join(hidden, xlsxListSeparator))
	}

	return nil
}

func isXlsxRowEmpty(row xlsxRow) bool {
	for _, cell := range row.Cells {
		if strings.TrimSpace(cell.Value) != "" {
			return false
		}
	}

	return true
}

func mapXlsxHeader(header xlsxRow) ([xlsxColumnCount]int, error) {
	var columns [xlsxColumnCount]int
	for i := range columns {
		columns[i] = -1
	}

	for _, col := range sortedXlsxColumns(header.Cells) {
		cell := header.Cells[col]
		if cell.Type != "" {
			continue
		}

		name := strings.TrimSpace(cell.Value)
		for i, spec := range xlsxColumnSpecs {
			if !matchXlsxHeader(name, spec.aliases) {
				continue
			}
			if columns[i] >= 0 {
				return columns, gerrors.Newf(gerrors.InvalidParameter, errXlsxHeaderDuplicateFmt, xlsxColumnLabel(i))
			}
			columns[i] = col
		}
	}

	for i, spec := range xlsxColumnSpecs {
		if spec.required && columns[i] < 0 {
			return columns, gerrors.Newf(gerrors.InvalidParameter, errXlsxHeaderMissingFmt, xlsxColumnLabel(i))
		}
	}

	return columns, nil
}

func matchXlsxHeader(name string, aliases []string) bool {
	for _, alias := range aliases {
		if strings.EqualFold(name, alias) {
			return true
		}
	}

	return false
}

func xlsxColumnLabel(index int) string {
	return strings.Join(xlsxColumnSpecs[index].aliases, xlsxAliasSeparator)
}

func extractXlsxSourceRow(row xlsxRow, columns [xlsxColumnCount]int) (xlsxSourceRow, error) {
	sourceRow := xlsxSourceRow{Row: row.Num}
	for i, spec := range xlsxColumnSpecs {
		if columns[i] < 0 {
			continue
		}

		cell, ok := row.Cells[columns[i]]
		if !ok {
			continue
		}

		if cell.Type != "" {
			if spec.required {
				return xlsxSourceRow{}, gerrors.Newf(
					gerrors.InvalidParameter, errXlsxUnsupportedCellFmt, row.Num, xlsxColumnLabel(i), cell.Type,
				)
			}
			continue
		}

		sourceRow.Values[i] = cell.Value
	}

	return sourceRow, nil
}

func buildXlsxRecords(src xlsxSource, params xlsxParams) ([]importAddTemplateRecord, error) {
	byID := make(map[int]xlsxKeptRecord, len(src.Rows))
	byName := make(map[string]xlsxKeptRecord, len(src.Rows))
	records := make([]importAddTemplateRecord, 0, len(src.Rows))

	for _, sourceRow := range src.Rows {
		record, err := convertXlsxSourceRow(sourceRow, params)
		if err != nil {
			return nil, err
		}

		if kept, ok := byID[record.ClusterID]; ok {
			if err := checkXlsxSameCluster(sourceRow.Row, kept, record); err != nil {
				return nil, err
			}
			continue
		}

		if kept, ok := byName[record.ClusterName]; ok {
			return nil, gerrors.Newf(
				gerrors.InvalidParameter, errXlsxDuplicateConflFmt, sourceRow.Row, kept.row, xlsxReasonNameIDConfl,
			)
		}

		if err := validateImportAdd(importRecordFromAddTemplate(record)); err != nil {
			return nil, gerrors.Newf(gerrors.InvalidParameter, errXlsxValidateRecordFmt, sourceRow.Row, err)
		}

		kept := xlsxKeptRecord{row: sourceRow.Row, record: record}
		byID[record.ClusterID] = kept
		byName[record.ClusterName] = kept
		records = append(records, record)
	}

	return records, nil
}

func convertXlsxSourceRow(sourceRow xlsxSourceRow, params xlsxParams) (importAddTemplateRecord, error) {
	rawClusterID := sourceRow.Values[xlsxColClusterID]
	clusterID, reason := parseXlsxInteger(rawClusterID, xlsxReasonPositiveInt)
	if reason == "" && clusterID <= 0 {
		reason = xlsxReasonPositiveInt
	}
	if reason != "" {
		return importAddTemplateRecord{}, newXlsxCellError(sourceRow.Row, xlsxColClusterID, rawClusterID, reason)
	}

	rawDomain := sourceRow.Values[xlsxColDomain]
	domain, _, reason := normalizeXlsxDomain(rawDomain)
	if reason != "" {
		return importAddTemplateRecord{}, newXlsxCellError(sourceRow.Row, xlsxColDomain, rawDomain, reason)
	}

	rawCloudID := sourceRow.Values[xlsxColBkCloudID]
	bkCloudID, reason := parseXlsxInteger(rawCloudID, xlsxReasonNonNegInt)
	if reason != "" {
		return importAddTemplateRecord{}, newXlsxCellError(sourceRow.Row, xlsxColBkCloudID, rawCloudID, reason)
	}

	return importAddTemplateRecord{
		Action:        importActionAdd,
		BkBizID:       params.BkBizID,
		BkCloudID:     bkCloudID,
		ClusterID:     clusterID,
		ClusterName:   domain,
		SwitchVersion: params.SwitchVersion,
		Status:        params.Status,
	}, nil
}

func newXlsxCellError(row int, column int, value string, reason string) error {
	if strings.TrimSpace(value) == "" {
		reason = xlsxReasonRequired
	}

	return gerrors.Newf(gerrors.InvalidParameter, errXlsxCellInvalidFmt, row, xlsxColumnLabel(column), value, reason)
}

func checkXlsxSameCluster(row int, kept xlsxKeptRecord, record importAddTemplateRecord) error {
	if kept.record.ClusterName != record.ClusterName {
		return gerrors.Newf(gerrors.InvalidParameter, errXlsxDuplicateConflFmt, row, kept.row, xlsxReasonIDNameConfl)
	}

	if kept.record.BkCloudID != record.BkCloudID {
		return gerrors.Newf(gerrors.InvalidParameter, errXlsxDuplicateConflFmt, row, kept.row, xlsxReasonIDCloudConfl)
	}

	return nil
}

func importRecordFromAddTemplate(record importAddTemplateRecord) importRecord {
	return importRecord{
		Action:        record.Action,
		BkBizID:       record.BkBizID,
		BkCloudID:     record.BkCloudID,
		ClusterID:     record.ClusterID,
		ClusterName:   record.ClusterName,
		SwitchVersion: record.SwitchVersion,
		Status:        record.Status,
	}
}

// parseXlsxInteger accepts non-negative integers up to math.MaxInt32, including the "123.0" form written by
// spreadsheets, and returns invalidReason or xlsxReasonIntRange on failure.
func parseXlsxInteger(raw string, invalidReason string) (int, string) {
	matches := xlsxIntegerPattern.FindStringSubmatch(strings.TrimSpace(raw))
	if matches == nil {
		return 0, invalidReason
	}

	value, err := strconv.Atoi(matches[1])
	if err != nil || value > math.MaxInt32 {
		return 0, xlsxReasonIntRange
	}

	return value, ""
}

// normalizeXlsxDomain returns the host, whether a numeric port was removed, and a failure reason. The host may
// only use letters, digits, '.', '-' or '_'.
func normalizeXlsxDomain(raw string) (string, bool, string) {
	domain := strings.TrimSpace(raw)
	if domain == "" {
		return "", false, xlsxReasonRequired
	}

	if strings.ContainsAny(domain, xlsxDomainSplitSets) {
		return "", false, xlsxReasonMultiDomain
	}

	host, portRemoved := domain, false
	if idx := strings.LastIndex(domain, ":"); idx >= 0 {
		port := domain[idx+1:]
		host, portRemoved = domain[:idx], true
		if port == "" || strings.Trim(port, "0123456789") != "" || strings.Contains(host, ":") {
			return "", false, xlsxReasonInvalidPort
		}

		if host == "" {
			return "", false, xlsxReasonRequired
		}
	}

	// The charset check runs after the port check because ':' is not an allowed host character.
	if strings.Trim(host, xlsxDomainAllowedChars) != "" {
		return "", false, xlsxReasonDomainChars
	}

	return host, portRemoved, ""
}

func writeXlsxTemplateTemp(filePath string, records []importAddTemplateRecord) error {
	var buf bytes.Buffer
	for _, record := range records {
		line, err := json.Marshal(record)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, errFormatOutputFormat, err)
		}
		buf.Write(line)
		buf.WriteByte('\n')
	}

	if err := os.WriteFile(filePath, buf.Bytes(), 0o644); err != nil {
		return gerrors.Newf(gerrors.Failure, errXlsxWriteFileFmt, filePath, err)
	}

	return nil
}

type xlsxCell struct {
	Value string
	// Type is empty for supported cell types, otherwise it keeps the raw unsupported t attribute.
	Type string
}

type xlsxRow struct {
	Num    int
	Hidden bool
	Cells  map[int]xlsxCell
}

type xlsxWorkbookXML struct {
	Sheets []xlsxSheetXML `xml:"sheets>sheet"`
}

type xlsxSheetXML struct {
	Name  string `xml:"name,attr"`
	RelID string `xml:"http://schemas.openxmlformats.org/officeDocument/2006/relationships id,attr"`
}

type xlsxRelsXML struct {
	Items []xlsxRelXML `xml:"Relationship"`
}

type xlsxRelXML struct {
	ID     string `xml:"Id,attr"`
	Target string `xml:"Target,attr"`
}

type xlsxSharedStringsXML struct {
	Items []xlsxStringItemXML `xml:"si"`
}

// xlsxStringItemXML only maps t and r children, so phonetic rPh text is skipped.
type xlsxStringItemXML struct {
	Text string       `xml:"t"`
	Runs []xlsxRunXML `xml:"r"`
}

type xlsxRunXML struct {
	Text string `xml:"t"`
}

type xlsxWorksheetXML struct {
	Rows []xlsxRowXML `xml:"sheetData>row"`
}

type xlsxRowXML struct {
	Num    int           `xml:"r,attr"`
	Hidden string        `xml:"hidden,attr"`
	Cells  []xlsxCellXML `xml:"c"`
}

type xlsxCellXML struct {
	Ref    string             `xml:"r,attr"`
	Type   string             `xml:"t,attr"`
	Value  string             `xml:"v"`
	Inline *xlsxStringItemXML `xml:"is"`
}

func (item xlsxStringItemXML) text() string {
	var builder strings.Builder
	builder.WriteString(item.Text)
	for _, run := range item.Runs {
		builder.WriteString(run.Text)
	}

	return builder.String()
}

func readXlsxRows(filePath string) ([]xlsxRow, error) {
	reader, err := zip.OpenReader(filePath)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, errXlsxOpenFmt, filePath, err)
	}
	defer reader.Close()

	entries := make(map[string]*zip.File, len(reader.File))
	for _, file := range reader.File {
		entries[file.Name] = file
	}

	sheetPath, err := locateXlsxSheet(entries)
	if err != nil {
		return nil, err
	}

	shared, err := readXlsxSharedStrings(entries)
	if err != nil {
		return nil, err
	}

	var sheet xlsxWorksheetXML
	if err := decodeXlsxEntry(entries, sheetPath, &sheet); err != nil {
		return nil, err
	}

	return convertXlsxRows(sheet.Rows, shared)
}

func readXlsxEntry(entries map[string]*zip.File, name string) ([]byte, bool, error) {
	file, ok := entries[name]
	if !ok {
		return nil, false, nil
	}

	if file.UncompressedSize64 > xlsxMaxEntrySize {
		return nil, true, gerrors.Newf(gerrors.InvalidParameter, errXlsxEntryTooLargeFmt, name, xlsxMaxEntrySize)
	}

	rc, err := file.Open()
	if err != nil {
		return nil, true, gerrors.Newf(gerrors.Failure, errXlsxReadEntryFmt, name, err)
	}
	defer rc.Close()

	data, err := io.ReadAll(io.LimitReader(rc, xlsxMaxEntrySize+1))
	if err != nil {
		return nil, true, gerrors.Newf(gerrors.Failure, errXlsxReadEntryFmt, name, err)
	}

	if len(data) > xlsxMaxEntrySize {
		return nil, true, gerrors.Newf(gerrors.InvalidParameter, errXlsxEntryTooLargeFmt, name, xlsxMaxEntrySize)
	}

	return data, true, nil
}

func decodeXlsxEntry(entries map[string]*zip.File, name string, v any) error {
	data, ok, err := readXlsxEntry(entries, name)
	if err != nil {
		return err
	}

	if !ok {
		return gerrors.Newf(gerrors.InvalidParameter, errXlsxEntryMissingFmt, name)
	}

	if err := xml.Unmarshal(data, v); err != nil {
		return gerrors.Newf(gerrors.InvalidParameter, errXlsxParseEntryFmt, name, err)
	}

	return nil
}

func locateXlsxSheet(entries map[string]*zip.File) (string, error) {
	var workbook xlsxWorkbookXML
	if err := decodeXlsxEntry(entries, xlsxPathWorkbook, &workbook); err != nil {
		return "", err
	}

	if len(workbook.Sheets) != 1 {
		names := make([]string, 0, len(workbook.Sheets))
		for _, sheet := range workbook.Sheets {
			names = append(names, sheet.Name)
		}

		return "", gerrors.Newf(
			gerrors.InvalidParameter, errXlsxMultipleSheetsFmt, strings.Join(names, xlsxListSeparator),
		)
	}

	var rels xlsxRelsXML
	if err := decodeXlsxEntry(entries, xlsxPathWorkbookRels, &rels); err != nil {
		return "", err
	}

	for _, rel := range rels.Items {
		if rel.ID == workbook.Sheets[0].RelID {
			return resolveXlsxTarget(rel.Target), nil
		}
	}

	return "", gerrors.Newf(
		gerrors.InvalidParameter, errXlsxParseEntryFmt, xlsxPathWorkbookRels, xlsxReasonSheetNotFound,
	)
}

func resolveXlsxTarget(target string) string {
	if strings.HasPrefix(target, "/") {
		return strings.TrimPrefix(path.Clean(target), "/")
	}

	return path.Join(xlsxPathBaseDir, target)
}

func readXlsxSharedStrings(entries map[string]*zip.File) ([]string, error) {
	data, ok, err := readXlsxEntry(entries, xlsxPathSharedStrings)
	if err != nil || !ok {
		return nil, err
	}

	var sst xlsxSharedStringsXML
	if err := xml.Unmarshal(data, &sst); err != nil {
		return nil, gerrors.Newf(gerrors.InvalidParameter, errXlsxParseEntryFmt, xlsxPathSharedStrings, err)
	}

	shared := make([]string, 0, len(sst.Items))
	for _, item := range sst.Items {
		shared = append(shared, item.text())
	}

	return shared, nil
}

func convertXlsxRows(rowsXML []xlsxRowXML, shared []string) ([]xlsxRow, error) {
	rows := make([]xlsxRow, 0, len(rowsXML))
	prevNum := 0
	for _, rowXML := range rowsXML {
		num := rowXML.Num
		if num <= 0 {
			num = prevNum + 1
		}
		prevNum = num

		cells, err := convertXlsxCells(num, rowXML.Cells, shared)
		if err != nil {
			return nil, err
		}

		hidden := rowXML.Hidden == xlsxBoolOne || rowXML.Hidden == xlsxBoolTrue
		rows = append(rows, xlsxRow{Num: num, Hidden: hidden, Cells: cells})
	}

	return rows, nil
}

func convertXlsxCells(rowNum int, cellsXML []xlsxCellXML, shared []string) (map[int]xlsxCell, error) {
	cells := make(map[int]xlsxCell, len(cellsXML))
	prevCol := -1
	for _, cellXML := range cellsXML {
		col := prevCol + 1
		if cellXML.Ref != "" {
			parsed, ok := parseXlsxColumn(cellXML.Ref)
			if !ok {
				return nil, gerrors.Newf(gerrors.InvalidParameter, errXlsxRowInvalidFmt, rowNum, xlsxReasonInvalidRef)
			}
			col = parsed
		}
		prevCol = col

		cell, ok := resolveXlsxCell(cellXML, shared)
		if !ok {
			return nil, gerrors.Newf(gerrors.InvalidParameter, errXlsxRowInvalidFmt, rowNum, xlsxReasonSharedIndex)
		}
		cells[col] = cell
	}

	return cells, nil
}

// parseXlsxColumn converts a cell reference such as "AB12" to a zero-based column index.
func parseXlsxColumn(ref string) (int, bool) {
	col := 0
	letters := 0
	for _, ch := range ref {
		if ch < 'A' || ch > 'Z' {
			break
		}
		col = col*26 + int(ch-'A'+1)
		letters++
	}

	rest := ref[letters:]
	if letters == 0 || letters > 3 || rest == "" || strings.Trim(rest, "0123456789") != "" {
		return 0, false
	}

	return col - 1, true
}

func resolveXlsxCell(cellXML xlsxCellXML, shared []string) (xlsxCell, bool) {
	switch cellXML.Type {
	case xlsxCellTypeShared:
		idx, err := strconv.Atoi(strings.TrimSpace(cellXML.Value))
		if err != nil || idx < 0 || idx >= len(shared) {
			return xlsxCell{}, false
		}
		return xlsxCell{Value: shared[idx]}, true

	case xlsxCellTypeInline:
		if cellXML.Inline == nil {
			return xlsxCell{}, true
		}
		return xlsxCell{Value: cellXML.Inline.text()}, true

	case "", xlsxCellTypeNumber, xlsxCellTypeFormula:
		return xlsxCell{Value: cellXML.Value}, true

	case xlsxCellTypeBool, xlsxCellTypeError, xlsxCellTypeDate:
		return xlsxCell{Value: cellXML.Value, Type: cellXML.Type}, true

	default:
		return xlsxCell{Value: cellXML.Value, Type: cellXML.Type}, true
	}
}

func sortedXlsxColumns(cells map[int]xlsxCell) []int {
	cols := make([]int, 0, len(cells))
	for col := range cells {
		cols = append(cols, col)
	}
	sort.Ints(cols)

	return cols
}
