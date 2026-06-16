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
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/tools/internal/bwmgr"
)

type importRecord struct {
	Action           string `json:"action"`
	ID               int    `json:"id,omitempty"`
	BkBizID          int    `json:"bk_biz_id,omitempty"`
	BkCloudID        int    `json:"bk_cloud_id,omitempty"`
	ClusterID        int    `json:"cluster_id,omitempty"`
	ClusterName      string `json:"cluster_name,omitempty"`
	SetClusterName   string `json:"set_cluster_name,omitempty"`
	SwitchVersion    string `json:"switch_version,omitempty"`
	Status           string `json:"status,omitempty"`
	ClusterNameSet   bool   `json:"-"`
	SwitchVersionSet bool   `json:"-"`
	StatusSet        bool   `json:"-"`
}

type importEntry struct {
	Line   int
	Record importRecord
}

type importResult struct {
	Added   int
	Updated int
	Deleted int
}

const importScannerMaxCapacity = 1024 * 1024

type importAddTemplateRecord struct {
	Action        string `json:"action"`
	BkBizID       int    `json:"bk_biz_id"`
	BkCloudID     int    `json:"bk_cloud_id"`
	ClusterID     int    `json:"cluster_id"`
	ClusterName   string `json:"cluster_name"`
	SwitchVersion string `json:"switch_version"`
	Status        string `json:"status"`
}

type importUpdateTemplateRecord struct {
	Action         string `json:"action"`
	ID             int    `json:"id"`
	BkBizID        int    `json:"bk_biz_id"`
	BkCloudID      int    `json:"bk_cloud_id"`
	ClusterID      int    `json:"cluster_id"`
	ClusterName    string `json:"cluster_name"`
	SetClusterName string `json:"set_cluster_name"`
	SwitchVersion  string `json:"switch_version"`
	Status         string `json:"status"`
}

type importDeleteTemplateRecord struct {
	Action      string `json:"action"`
	ID          int    `json:"id"`
	BkBizID     int    `json:"bk_biz_id"`
	BkCloudID   int    `json:"bk_cloud_id"`
	ClusterID   int    `json:"cluster_id"`
	ClusterName string `json:"cluster_name"`
}

type importExportUpdateRecord struct {
	Action        string `json:"action"`
	ID            int    `json:"id"`
	BkBizID       int    `json:"bk_biz_id"`
	BkCloudID     int    `json:"bk_cloud_id"`
	ClusterID     int    `json:"cluster_id"`
	ClusterName   string `json:"cluster_name"`
	SwitchVersion string `json:"switch_version"`
	Status        string `json:"status"`
}

// Import handles the import command.
func (h *Handler) Import(opts ImportOptions) error {
	if opts.CreateTemplate != "" && opts.CreateTemplateFromList != "" {
		return gerrors.Newf(gerrors.InvalidParameter, errImportTemplateMutualExclusive)
	}
	if opts.CreateTemplateFromList != "" {
		return h.writeImportTemplateFromList(opts.CreateTemplateFromList)
	}
	if opts.CreateTemplate != "" {
		return writeImportTemplate(opts.CreateTemplate)
	}

	entries, err := readImportEntries(opts.File)
	if err != nil {
		return err
	}
	if err := validateImportEntries(entries); err != nil {
		return err
	}

	if opts.DryRun {
		fmt.Printf(msgImportDryRunFormat, len(entries))
		return nil
	}

	if err := confirmImport(opts, entries); err != nil {
		return err
	}

	result, err := h.executeImportEntries(entries, opts)
	if err != nil {
		return err
	}

	fmt.Printf(msgImportSuccessFormat, result.Added, result.Updated, result.Deleted)
	return nil
}

func writeImportTemplate(path string) error {
	content, err := buildImportTemplateContent()
	if err != nil {
		return err
	}

	if err := os.WriteFile(path, content, 0o644); err != nil {
		return gerrors.Newf(gerrors.Failure, errImportWriteTmplFmt, err)
	}

	fmt.Printf(msgImportTemplateFmt, path)
	return nil
}

func buildImportTemplateContent() ([]byte, error) {
	records := []any{
		importAddTemplateRecord{Action: importActionAdd},
		importUpdateTemplateRecord{Action: importActionUpdate},
		importDeleteTemplateRecord{Action: importActionDelete},
	}

	var buf bytes.Buffer
	for _, record := range records {
		line, err := json.Marshal(record)
		if err != nil {
			return nil, gerrors.Newf(gerrors.Failure, errFormatOutputFormat, err)
		}
		buf.Write(line)
		buf.WriteByte('\n')
	}

	return buf.Bytes(), nil
}

func (h *Handler) writeImportTemplateFromList(path string) error {
	items, err := h.service.GetBlackWhiteList(h.bkCloudID, nil)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, errGetListFormat, err)
	}

	content, err := buildImportTemplateFromListContent(items)
	if err != nil {
		return err
	}

	if err := os.WriteFile(path, content, 0o644); err != nil {
		return gerrors.Newf(gerrors.Failure, errImportWriteTmplFmt, err)
	}

	fmt.Printf(msgImportTemplateFromListFmt, path)
	return nil
}

func buildImportTemplateFromListContent(items []bwmgr.BlackWhiteListItem) ([]byte, error) {
	var buf bytes.Buffer
	for _, item := range items {
		line, err := json.Marshal(buildExportUpdateRecord(item))
		if err != nil {
			return nil, gerrors.Newf(gerrors.Failure, errFormatOutputFormat, err)
		}
		buf.Write(line)
		buf.WriteByte('\n')
	}

	return buf.Bytes(), nil
}

func buildExportUpdateRecord(item bwmgr.BlackWhiteListItem) importExportUpdateRecord {
	return importExportUpdateRecord{
		Action:        importActionUpdate,
		ID:            int(item.ID),
		BkBizID:       item.BkBizID,
		BkCloudID:     item.BkCloudID,
		ClusterID:     item.ClusterID,
		ClusterName:   item.ClusterName,
		SwitchVersion: string(item.SwitchVersion),
		Status:        string(item.Status),
	}
}

func readImportEntries(path string) ([]importEntry, error) {
	if path == "" {
		return nil, gerrors.Newf(gerrors.InvalidParameter, errImportFileRequired)
	}

	file, err := os.Open(path)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, errImportReadFileFmt, err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 0, 64*1024), importScannerMaxCapacity)

	return scanImportEntries(scanner)
}

func scanImportEntries(scanner *bufio.Scanner) ([]importEntry, error) {
	entries := make([]importEntry, 0)
	lineNo := 0

	for scanner.Scan() {
		lineNo++
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		entry, err := parseImportEntry(lineNo, line)
		if err != nil {
			return nil, err
		}
		entries = append(entries, entry)
	}

	if err := scanner.Err(); err != nil {
		return nil, gerrors.Newf(gerrors.Failure, errImportReadFileFmt, err)
	}

	return entries, nil
}

func parseImportEntry(lineNo int, line string) (importEntry, error) {
	var raw map[string]json.RawMessage
	if err := json.Unmarshal([]byte(line), &raw); err != nil {
		return importEntry{}, gerrors.Newf(gerrors.InvalidJson, errImportParseLineFmt, lineNo, err)
	}

	var record importRecord
	if err := json.Unmarshal([]byte(line), &record); err != nil {
		return importEntry{}, gerrors.Newf(gerrors.InvalidJson, errImportParseLineFmt, lineNo, err)
	}
	_, record.ClusterNameSet = raw["cluster_name"]
	_, record.SwitchVersionSet = raw["switch_version"]
	_, record.StatusSet = raw["status"]

	return importEntry{Line: lineNo, Record: record}, nil
}

func validateImportEntries(entries []importEntry) error {
	for _, entry := range entries {
		if err := validateImportEntry(entry); err != nil {
			return gerrors.Newf(gerrors.InvalidParameter, errImportValidateLineFmt, entry.Line, err)
		}
	}

	return nil
}

func validateImportEntry(entry importEntry) error {
	switch entry.Record.Action {
	case importActionAdd:
		return validateImportAdd(entry.Record)

	case importActionUpdate:
		_, err := buildUpdateRequest(importUpdateOptions(entry.Record, true))
		return err

	case importActionDelete:
		_, err := buildDeleteRequest(importDeleteOptions(entry.Record, true))
		return err

	default:
		return gerrors.Newf(gerrors.InvalidParameter, errImportInvalidAction)
	}
}

func validateImportAdd(record importRecord) error {
	req := buildInsertRequest(importAddOptions(record, false, false, nil))
	if err := req.Validate(); err != nil {
		return gerrors.Newf(gerrors.InvalidParameter, errAddEntryFormat, err)
	}

	return nil
}

func confirmImport(opts ImportOptions, entries []importEntry) error {
	if opts.Yes || !hasRiskyImport(entries, opts.Upsert) {
		return nil
	}

	if opts.Confirm == nil || !opts.Confirm(warnImportRisky) {
		return gerrors.Newf(gerrors.Failure, errImportCancelled)
	}

	return nil
}

func hasRiskyImport(entries []importEntry, upsert bool) bool {
	if upsert {
		return true
	}

	for _, entry := range entries {
		if entry.Record.Action == importActionUpdate || entry.Record.Action == importActionDelete {
			return true
		}
	}

	return false
}

func (h *Handler) executeImportEntries(entries []importEntry, opts ImportOptions) (importResult, error) {
	result := importResult{}

	for _, entry := range entries {
		if err := h.executeImportEntry(entry, opts, &result); err != nil {
			return importResult{}, gerrors.Newf(gerrors.Failure, errImportLineFailedFmt, entry.Line, err)
		}
	}

	return result, nil
}

func (h *Handler) executeImportEntry(entry importEntry, opts ImportOptions, result *importResult) error {
	switch entry.Record.Action {
	case importActionAdd:
		addResult, err := h.addEntry(importAddOptions(entry.Record, opts.Upsert, true, opts.Confirm))
		if err != nil {
			return err
		}
		countImportAddResult(addResult, result)
		return nil

	case importActionUpdate:
		rowsAffected, err := h.updateEntry(importUpdateOptions(entry.Record, true))
		if err != nil {
			return err
		}
		result.Updated += rowsAffected
		return nil

	case importActionDelete:
		rowsAffected, err := h.deleteEntry(importDeleteOptions(entry.Record, true))
		if err != nil {
			return err
		}
		result.Deleted += rowsAffected
		return nil

	default:
		return gerrors.Newf(gerrors.InvalidParameter, errImportInvalidAction)
	}
}

func countImportAddResult(addResult addEntryResult, result *importResult) {
	if addResult.Updated {
		result.Updated += addResult.RowsAffected
		return
	}

	result.Added++
}

func importAddOptions(record importRecord, upsert bool, yes bool, confirm ConfirmFunc) AddOptions {
	return AddOptions{
		BkBizID:          record.BkBizID,
		BkCloudID:        record.BkCloudID,
		ClusterID:        record.ClusterID,
		ClusterName:      record.ClusterName,
		SwitchVersion:    record.SwitchVersion,
		Status:           record.Status,
		Upsert:           upsert,
		Yes:              yes,
		Confirm:          confirm,
		ClusterNameSet:   record.ClusterNameSet,
		SwitchVersionSet: record.SwitchVersionSet,
		StatusSet:        record.StatusSet,
	}
}

func importUpdateOptions(record importRecord, yes bool) UpdateOptions {
	return UpdateOptions{
		ID:             record.ID,
		BkBizID:        record.BkBizID,
		BkCloudID:      record.BkCloudID,
		ClusterID:      record.ClusterID,
		ClusterName:    record.ClusterName,
		SetClusterName: record.SetClusterName,
		SwitchVersion:  record.SwitchVersion,
		Status:         record.Status,
		Yes:            yes,
	}
}

func importDeleteOptions(record importRecord, yes bool) DeleteOptions {
	return DeleteOptions{
		ID:          record.ID,
		BkBizID:     record.BkBizID,
		BkCloudID:   record.BkCloudID,
		ClusterID:   record.ClusterID,
		ClusterName: record.ClusterName,
		Yes:         yes,
	}
}
