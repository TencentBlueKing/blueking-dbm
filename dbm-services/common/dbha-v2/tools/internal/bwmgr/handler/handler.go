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

// Package handler implements command handlers for the bwmgr CLI.
package handler

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"text/tabwriter"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/tools/internal/bwmgr"
	"dbm-services/common/dbha-v2/tools/internal/bwmgr/config"
)

// Handler represents the black-white list command handler
type Handler struct {
	service   BlackWhiteListService
	bkCloudID int
}

type addEntryResult struct {
	ID           uint
	RowsAffected int
	Updated      bool
}

// NewHandler creates a new command handler
func NewHandler(cfg *config.Config) *Handler {
	client := bwmgr.NewClient(cfg.GetAPIURL(), cfg.API.Token, cfg.API.Timeout)

	return NewHandlerWithService(cfg.API.BkCloudID, client)
}

// NewHandlerWithService creates a handler with an injected service.
func NewHandlerWithService(bkCloudID int, service BlackWhiteListService) *Handler {
	return &Handler{
		service:   service,
		bkCloudID: bkCloudID,
	}
}

// List handles the list command.
func (h *Handler) List(opts ListOptions) error {
	queryArgs, err := buildListRequest(opts)
	if err != nil {
		return err
	}

	items, err := h.service.GetBlackWhiteList(h.bkCloudID, queryArgs)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, errGetListFormat, err)
	}

	return writeListOutput(os.Stdout, items, opts)
}

// Add handles the add command.
func (h *Handler) Add(opts AddOptions) error {
	result, err := h.addEntry(opts)
	if err != nil {
		return err
	}

	if result.Updated {
		fmt.Printf(msgAddUpsertFormat, result.RowsAffected)
		return nil
	}

	fmt.Printf(msgAddSuccessFormat, result.ID)
	return nil
}

func (h *Handler) addEntry(opts AddOptions) (addEntryResult, error) {
	if opts.BkBizID == 0 {
		return addEntryResult{}, gerrors.Newf(gerrors.InvalidParameter, errBkBizIDRequired)
	}

	if opts.ClusterID == 0 {
		return addEntryResult{}, gerrors.Newf(gerrors.InvalidParameter, errClusterIDRequired)
	}

	if opts.Upsert {
		return h.upsertAddEntry(opts)
	}

	return h.insertAddEntry(opts)
}

func (h *Handler) insertAddEntry(opts AddOptions) (addEntryResult, error) {
	if opts.ClusterName == "" {
		return addEntryResult{}, gerrors.Newf(gerrors.InvalidParameter, errClusterNameRequired)
	}

	insertReq := buildInsertRequest(opts)
	if err := insertReq.Validate(); err != nil {
		return addEntryResult{}, gerrors.Newf(gerrors.InvalidParameter, errAddEntryFormat, err)
	}

	id, err := h.service.InsertBlackWhiteList(h.bkCloudID, insertReq)
	if err != nil {
		return addEntryResult{}, gerrors.Newf(gerrors.Failure, errAddEntryFormat, err)
	}

	return addEntryResult{ID: id}, nil
}

func (h *Handler) upsertAddEntry(opts AddOptions) (addEntryResult, error) {
	matches, err := h.findAddMatches(opts)
	if err != nil {
		return addEntryResult{}, err
	}
	if len(matches) == 0 {
		return h.insertAddEntry(opts)
	}
	if len(matches) > 1 {
		return addEntryResult{}, gerrors.Newf(
			gerrors.InvalidParameter,
			errAddUpsertConflictFmt,
			opts.BkBizID,
			opts.BkCloudID,
			opts.ClusterID,
		)
	}

	updateReq, err := buildAddUpsertUpdateRequest(matches[0].ID, opts)
	if err != nil {
		return addEntryResult{}, err
	}

	confirmOpts := UpdateOptions{Yes: opts.Yes, Confirm: opts.Confirm}
	if err := confirmRiskyUpdate(confirmOpts, updateReq); err != nil {
		return addEntryResult{}, err
	}

	rowsAffected, err := h.service.UpdateBlackWhiteList(h.bkCloudID, updateReq)
	if err != nil {
		return addEntryResult{}, gerrors.Newf(gerrors.Failure, errUpdateEntryFormat, err)
	}

	return addEntryResult{RowsAffected: rowsAffected, Updated: true}, nil
}

func buildInsertRequest(opts AddOptions) bwmgr.InsertBlackWhiteListRequest {
	return bwmgr.InsertBlackWhiteListRequest{
		BkBizID:       opts.BkBizID,
		BkCloudID:     opts.BkCloudID,
		ClusterID:     opts.ClusterID,
		ClusterName:   opts.ClusterName,
		SwitchVersion: bwmgr.SwitchVersionType(opts.SwitchVersion),
		Status:        bwmgr.StatusType(opts.Status),
	}
}

func (h *Handler) findAddMatches(opts AddOptions) ([]bwmgr.BlackWhiteListItem, error) {
	queryArgs := buildGetQueryArgs(queryOptions{
		BkBizID:   opts.BkBizID,
		BkCloudID: opts.BkCloudID,
		ClusterID: opts.ClusterID,
	})

	items, err := h.service.GetBlackWhiteList(h.bkCloudID, queryArgs)
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, errGetListFormat, err)
	}

	return items, nil
}

func buildAddUpsertUpdateRequest(id uint, opts AddOptions) (bwmgr.UpdateBlackWhiteListRequest, error) {
	updateReq := bwmgr.UpdateBlackWhiteListRequest{
		QueryArgs: bwmgr.UpdateQueryArgs{ID: &id},
	}

	if opts.ClusterNameSet {
		if opts.ClusterName == "" {
			return bwmgr.UpdateBlackWhiteListRequest{}, gerrors.Newf(
				gerrors.InvalidParameter,
				errClusterNameRequired,
			)
		}
		updateReq.SetArgs.ClusterName = &opts.ClusterName
	}

	if opts.SwitchVersionSet {
		switchVersion, err := parseSwitchVersion(opts.SwitchVersion)
		if err != nil {
			return bwmgr.UpdateBlackWhiteListRequest{}, err
		}
		updateReq.SetArgs.SwitchVersion = switchVersion
	}

	if opts.StatusSet {
		status, err := parseStatus(opts.Status)
		if err != nil {
			return bwmgr.UpdateBlackWhiteListRequest{}, err
		}
		updateReq.SetArgs.Status = status
	}

	if updateReq.SetArgs.ClusterName == nil &&
		updateReq.SetArgs.SwitchVersion == nil &&
		updateReq.SetArgs.Status == nil {
		return bwmgr.UpdateBlackWhiteListRequest{}, gerrors.Newf(
			gerrors.InvalidParameter,
			errAddUpsertSetRequired,
		)
	}

	return updateReq, nil
}

// Update handles the update command.
func (h *Handler) Update(opts UpdateOptions) error {
	rowsAffected, err := h.updateEntry(opts)
	if err != nil {
		return err
	}

	fmt.Printf(msgUpdateSuccessFormat, rowsAffected)
	return nil
}

func (h *Handler) updateEntry(opts UpdateOptions) (int, error) {
	updateReq, err := buildUpdateRequest(opts)
	if err != nil {
		return 0, err
	}

	if err := confirmRiskyUpdate(opts, updateReq); err != nil {
		return 0, err
	}

	rowsAffected, err := h.service.UpdateBlackWhiteList(h.bkCloudID, updateReq)
	if err != nil {
		return 0, gerrors.Newf(gerrors.Failure, errUpdateEntryFormat, err)
	}

	return rowsAffected, nil
}

// Delete handles the delete command.
func (h *Handler) Delete(opts DeleteOptions) error {
	rowsAffected, err := h.deleteEntry(opts)
	if err != nil {
		return err
	}

	fmt.Printf(msgDeleteSuccessFormat, rowsAffected)
	return nil
}

func (h *Handler) deleteEntry(opts DeleteOptions) (int, error) {
	deleteReq, err := buildDeleteRequest(opts)
	if err != nil {
		return 0, err
	}

	if err := confirmDelete(opts); err != nil {
		return 0, err
	}

	rowsAffected, err := h.service.DeleteBlackWhiteList(h.bkCloudID, deleteReq)
	if err != nil {
		return 0, gerrors.Newf(gerrors.Failure, errDeleteEntryFormat, err)
	}

	return rowsAffected, nil
}

func buildListRequest(opts ListOptions) (*bwmgr.GetBlackWhiteListRequest, error) {
	queryArgs := buildGetQueryArgs(queryOptions{
		BkBizID:     opts.BkBizID,
		BkCloudID:   opts.BkCloudID,
		ClusterID:   opts.ClusterID,
		ClusterName: opts.ClusterName,
	})

	switchVersion, err := parseSwitchVersion(opts.SwitchVersion)
	if err != nil {
		return nil, err
	}
	queryArgs.SwitchVersion = switchVersion

	status, err := parseStatus(opts.Status)
	if err != nil {
		return nil, err
	}
	queryArgs.Status = status

	return queryArgs, nil
}

func writeListOutput(w io.Writer, items []bwmgr.BlackWhiteListItem, opts ListOptions) error {
	if opts.OutputFile != "" {
		return writeListJSONLinesFile(items, opts.OutputFile)
	}

	switch opts.Output {
	case "", OutputFormatTable:
		return writeListTable(w, items)

	case OutputFormatJSON:
		return writeListJSON(w, items)

	default:
		return gerrors.Newf(gerrors.InvalidParameter, errOutputInvalid)
	}
}

func writeListTable(w io.Writer, items []bwmgr.BlackWhiteListItem) error {
	tw := tabwriter.NewWriter(w, 0, 0, 2, ' ', 0)
	if _, err := fmt.Fprintln(tw, listTableHeader); err != nil {
		return gerrors.Newf(gerrors.Failure, errWriteOutputFormat, err)
	}

	for _, item := range items {
		if _, err := fmt.Fprintf(
			tw,
			listTableRowFormat,
			item.ID,
			item.BkBizID,
			item.BkCloudID,
			item.ClusterID,
			item.ClusterName,
			item.SwitchVersion,
			item.Status,
			formatListTime(item.CreatedAt),
			formatListTime(item.UpdatedAt),
		); err != nil {
			return gerrors.Newf(gerrors.Failure, errWriteOutputFormat, err)
		}
	}

	if err := tw.Flush(); err != nil {
		return gerrors.Newf(gerrors.Failure, errWriteOutputFormat, err)
	}

	return nil
}

func writeListJSON(w io.Writer, items []bwmgr.BlackWhiteListItem) error {
	output, err := json.MarshalIndent(items, jsonIndentPrefix, jsonIndentValue)
	if err != nil {
		return gerrors.Newf(gerrors.InvalidJson, errFormatOutputFormat, err)
	}

	if _, err := fmt.Fprintln(w, string(output)); err != nil {
		return gerrors.Newf(gerrors.Failure, errWriteOutputFormat, err)
	}

	return nil
}

func writeListJSONLinesFile(items []bwmgr.BlackWhiteListItem, outputFile string) error {
	var output bytes.Buffer
	for _, item := range items {
		line, err := json.Marshal(item)
		if err != nil {
			return gerrors.Newf(gerrors.InvalidJson, errFormatOutputFormat, err)
		}

		output.Write(line)
		output.WriteByte('\n')
	}

	if err := os.WriteFile(outputFile, output.Bytes(), 0o644); err != nil {
		return gerrors.Newf(gerrors.Failure, errWriteOutputFileFmt, err)
	}

	return nil
}

func formatListTime(value time.Time) string {
	if value.IsZero() {
		return ""
	}

	return value.Format(time.RFC3339)
}

func buildUpdateRequest(opts UpdateOptions) (bwmgr.UpdateBlackWhiteListRequest, error) {
	if opts.ID == 0 && opts.BkBizID == 0 && opts.ClusterID == 0 && opts.ClusterName == "" {
		return bwmgr.UpdateBlackWhiteListRequest{}, gerrors.Newf(gerrors.InvalidParameter, errUpdateQueryRequired)
	}

	if opts.SetClusterName == "" && opts.SwitchVersion == "" && opts.Status == "" {
		return bwmgr.UpdateBlackWhiteListRequest{}, gerrors.Newf(gerrors.InvalidParameter, errUpdateSetRequired)
	}

	updateReq := bwmgr.UpdateBlackWhiteListRequest{}
	setUpdateQueryArgs(&updateReq, opts)

	if err := setUpdateSetArgs(&updateReq, opts); err != nil {
		return bwmgr.UpdateBlackWhiteListRequest{}, err
	}

	return updateReq, nil
}

func setUpdateQueryArgs(updateReq *bwmgr.UpdateBlackWhiteListRequest, opts UpdateOptions) {
	updateReq.QueryArgs = buildUpdateQueryArgs(queryOptions{
		ID:          opts.ID,
		BkBizID:     opts.BkBizID,
		BkCloudID:   opts.BkCloudID,
		ClusterID:   opts.ClusterID,
		ClusterName: opts.ClusterName,
	})
}

func setUpdateSetArgs(updateReq *bwmgr.UpdateBlackWhiteListRequest, opts UpdateOptions) error {
	if opts.SetClusterName != "" {
		updateReq.SetArgs.ClusterName = &opts.SetClusterName
	}

	switchVersion, err := parseSwitchVersion(opts.SwitchVersion)
	if err != nil {
		return err
	}
	updateReq.SetArgs.SwitchVersion = switchVersion

	status, err := parseStatus(opts.Status)
	if err != nil {
		return err
	}
	updateReq.SetArgs.Status = status

	return nil
}

func buildDeleteRequest(opts DeleteOptions) (bwmgr.DeleteBlackWhiteListRequest, error) {
	if opts.ID == 0 && opts.BkBizID == 0 && opts.ClusterID == 0 && opts.ClusterName == "" {
		return bwmgr.DeleteBlackWhiteListRequest{}, gerrors.Newf(gerrors.InvalidParameter, errDeleteParamRequired)
	}

	return buildDeleteQueryArgs(queryOptions{
		ID:          opts.ID,
		BkBizID:     opts.BkBizID,
		BkCloudID:   opts.BkCloudID,
		ClusterID:   opts.ClusterID,
		ClusterName: opts.ClusterName,
	}), nil
}

func buildGetQueryArgs(opts queryOptions) *bwmgr.GetBlackWhiteListRequest {
	queryArgs := buildCommonQueryArgs(opts)

	return &bwmgr.GetBlackWhiteListRequest{
		BkBizID:     queryArgs.BkBizID,
		BkCloudID:   queryArgs.BkCloudID,
		ClusterID:   queryArgs.ClusterID,
		ClusterName: queryArgs.ClusterName,
	}
}

func buildUpdateQueryArgs(opts queryOptions) bwmgr.UpdateQueryArgs {
	queryArgs := buildCommonQueryArgs(opts)

	return bwmgr.UpdateQueryArgs{
		ID:          queryArgs.ID,
		BkBizID:     queryArgs.BkBizID,
		BkCloudID:   queryArgs.BkCloudID,
		ClusterID:   queryArgs.ClusterID,
		ClusterName: queryArgs.ClusterName,
	}
}

func buildDeleteQueryArgs(opts queryOptions) bwmgr.DeleteBlackWhiteListRequest {
	queryArgs := buildCommonQueryArgs(opts)

	return bwmgr.DeleteBlackWhiteListRequest{
		ID:          queryArgs.ID,
		BkBizID:     queryArgs.BkBizID,
		BkCloudID:   queryArgs.BkCloudID,
		ClusterID:   queryArgs.ClusterID,
		ClusterName: queryArgs.ClusterName,
	}
}

func buildCommonQueryArgs(opts queryOptions) commonQueryArgs {
	queryArgs := commonQueryArgs{}

	if opts.ID > 0 {
		uid := uint(opts.ID)
		queryArgs.ID = &uid
	}

	if opts.BkBizID > 0 {
		queryArgs.BkBizID = &opts.BkBizID
	}

	if opts.BkCloudID >= 0 { // 0 is valid for direct region
		queryArgs.BkCloudID = &opts.BkCloudID
	}

	if opts.ClusterID > 0 {
		queryArgs.ClusterID = &opts.ClusterID
	}

	if opts.ClusterName != "" {
		queryArgs.ClusterName = &opts.ClusterName
	}

	return queryArgs
}

func parseSwitchVersion(value string) (*bwmgr.SwitchVersionType, error) {
	if value == "" {
		return nil, nil
	}

	switchVersion := bwmgr.SwitchVersionType(value)
	if switchVersion != bwmgr.SwitchVersionV1 && switchVersion != bwmgr.SwitchVersionV2 {
		return nil, gerrors.Newf(gerrors.InvalidParameter, errSwitchVersionInvalid)
	}

	return &switchVersion, nil
}

func parseStatus(value string) (*bwmgr.StatusType, error) {
	if value == "" {
		return nil, nil
	}

	status := bwmgr.StatusType(value)
	if status != bwmgr.StatusEnabled && status != bwmgr.StatusDisabled {
		return nil, gerrors.Newf(gerrors.InvalidParameter, errStatusInvalid)
	}

	return &status, nil
}

func confirmRiskyUpdate(opts UpdateOptions, updateReq bwmgr.UpdateBlackWhiteListRequest) error {
	if opts.Yes {
		return nil
	}

	disablingV2 := updateReq.SetArgs.Status != nil && *updateReq.SetArgs.Status == bwmgr.StatusDisabled
	switchingToV1 := updateReq.SetArgs.SwitchVersion != nil && *updateReq.SetArgs.SwitchVersion == bwmgr.SwitchVersionV1
	if !disablingV2 && !switchingToV1 {
		return nil
	}

	if opts.Confirm == nil || !opts.Confirm(warnUpdateRisky) {
		return gerrors.Newf(gerrors.Failure, errUpdateCancelled)
	}

	return nil
}

func confirmDelete(opts DeleteOptions) error {
	if opts.Yes {
		return nil
	}

	if opts.Confirm == nil || !opts.Confirm(warnDeleteRisky) {
		return gerrors.Newf(gerrors.Failure, errDeleteCancelled)
	}

	return nil
}
