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

// Package handler implements bwmgr command handlers.
package handler

const (
	// OutputFormatTable renders list results as a tabular stdout view.
	OutputFormatTable = "table"
	// OutputFormatJSON renders list results as indented JSON on stdout.
	OutputFormatJSON = "json"
)

const (
	jsonIndentPrefix = ""
	jsonIndentValue  = "  "
)

const (
	importActionAdd    = "add"
	importActionUpdate = "update"
	importActionDelete = "delete"
)

const (
	listTableHeader = "ID\tBK_BIZ_ID\tBK_CLOUD_ID\tCLUSTER_ID\tCLUSTER_NAME\tSWITCH_VERSION\tSTATUS\t" +
		"CREATED_AT\tUPDATED_AT"
	listTableRowFormat = "%d\t%d\t%d\t%d\t%s\t%s\t%s\t%s\t%s\n"
)

const (
	errSwitchVersionInvalid  = "switch-version must be 'v1' or 'v2'"
	errStatusInvalid         = "status must be 'enabled' or 'disabled'"
	errOutputInvalid         = "output must be 'table' or 'json'"
	errGetListFormat         = "failed to get black-white list: %v"
	errFormatOutputFormat    = "failed to format output: %v"
	errWriteOutputFormat     = "failed to write output: %v"
	errWriteOutputFileFmt    = "failed to write output file: %v"
	errImportFileRequired    = "file is required"
	errImportReadFileFmt     = "failed to read import file: %v"
	errImportWriteTmplFmt    = "failed to write import template: %v"
	errImportParseLineFmt    = "failed to parse import line %d: %v"
	errImportValidateLineFmt = "failed to validate import line %d: %v"
	errImportInvalidAction   = "action must be 'add', 'update', or 'delete'"
	errImportLineFailedFmt   = "failed to import line %d: %v"
	errAddUpsertConflictFmt  = "add matched multiple entries for bk_biz_id: %d, " +
		"bk_cloud_id: %d, cluster_id: %d"
	errAddUpsertSetRequired = "at least one upsert update field (cluster-name, switch-version, or status) " +
		"is required when matched entry exists"
	errBkBizIDRequired     = "bk-biz-id is required"
	errClusterIDRequired   = "cluster-id is required"
	errClusterNameRequired = "cluster-name is required"
	errAddEntryFormat      = "failed to add black-white list entry: %v"
	errUpdateQueryRequired = "at least one query parameter (id, bk-biz-id, cluster-id, or " +
		"cluster-name) is required"
	errUpdateSetRequired   = "at least one set parameter (set-cluster-name, switch-version, or status) is required"
	errUpdateCancelled     = "update operation cancelled by user"
	errUpdateEntryFormat   = "failed to update black-white list entry: %v"
	errDeleteParamRequired = "at least one parameter (id, bk-biz-id, cluster-id, or " +
		"cluster-name) is required"
	errDeleteCancelled               = "delete operation cancelled by user"
	errDeleteEntryFormat             = "failed to delete black-white list entry: %v"
	errImportCancelled               = "import operation cancelled by user"
	errImportTemplateMutualExclusive = "create-template and create-template-from-list cannot be used together"
)

const (
	msgAddSuccessFormat          = "Successfully added black-white list entry with ID: %d\n"
	msgAddUpsertFormat           = "Successfully upserted black-white list entry, rows affected: %d\n"
	msgUpdateSuccessFormat       = "Successfully updated %d black-white list entry(ies)\n"
	msgDeleteSuccessFormat       = "Successfully deleted %d black-white list entry(ies)\n"
	msgImportTemplateFmt         = "Successfully created import template: %s\n"
	msgImportTemplateFromListFmt = "Successfully created import template from list: %s\n"
	msgImportDryRunFormat        = "Import dry run passed, total: %d\n"
	msgImportSuccessFormat       = "Import finished, added: %d, updated: %d, deleted: %d\n"
)

const (
	warnUpdateRisky = "WARNING: this update may disable v2 white-listing and " +
		"affect ha-module(v1) switching behavior. Continue?"
	warnDeleteRisky = "WARNING: this will permanently delete the matched " +
		"black-white list entry(ies). Continue?"
	warnImportRisky = "WARNING: this import may update or delete black-white list entry(ies). Continue?"
)

const (
	xlsxHeaderClusterIDZh   = "集群 ID"
	xlsxHeaderClusterIDEn   = "Cluster ID"
	xlsxHeaderDomainZh      = "主域名"
	xlsxHeaderDomainEn      = "Primary domain name"
	xlsxHeaderBkCloudIDZh   = "管控区域"
	xlsxHeaderBkCloudIDEn   = "control area"
	xlsxHeaderClusterTypeZh = "集群类型"
	xlsxHeaderClusterTypeEn = "Cluster type"
	xlsxHeaderStatusZh      = "状态"
	xlsxHeaderStatusEn      = "state"
)

const (
	xlsxFieldBkBizID       = "bk_biz_id"
	xlsxFieldBkCloudID     = "bk_cloud_id"
	xlsxFieldClusterID     = "cluster_id"
	xlsxFieldClusterName   = "cluster_name"
	xlsxFieldSwitchVersion = "switch_version"
	xlsxFieldStatus        = "status"
	xlsxFieldAction        = "action"
)

const (
	xlsxBizFromFlag     = "flag"
	xlsxBizFromFilename = "filename"
	xlsxTempSuffix      = ".tmp"
	xlsxReportSuffix    = ".report.json"
	xlsxListSeparator   = ", "
	xlsxAliasSeparator  = "/"
	xlsxEmptyStatKey    = "-"
	xlsxResultPass      = "PASS"
	xlsxResultFail      = "FAIL"
	xlsxMaxTextDetails  = 20
	xlsxMaxEntrySize    = 64 << 20
	xlsxBoolTrue        = "true"
	xlsxBoolOne         = "1"
	xlsxDomainSplitSets = " \t\r\n,;，；"
)

const (
	xlsxCellTypeShared    = "s"
	xlsxCellTypeInline    = "inlineStr"
	xlsxCellTypeFormula   = "str"
	xlsxCellTypeNumber    = "n"
	xlsxCellTypeBool      = "b"
	xlsxCellTypeError     = "e"
	xlsxCellTypeDate      = "d"
	xlsxPathWorkbook      = "xl/workbook.xml"
	xlsxPathWorkbookRels  = "xl/_rels/workbook.xml.rels"
	xlsxPathSharedStrings = "xl/sharedStrings.xml"
	xlsxPathBaseDir       = "xl"
)

const (
	xlsxCheckImportable  = "importable"
	xlsxCheckFieldSet    = "field_set"
	xlsxCheckCoverage    = "row_coverage"
	xlsxCheckNoExtra     = "no_extra"
	xlsxCheckFieldMatch  = "field_match"
	xlsxCheckUnique      = "unique"
	xlsxCheckCount       = "count"
	xlsxCheckIDC1        = "C1"
	xlsxCheckIDC2        = "C2"
	xlsxCheckIDC3        = "C3"
	xlsxCheckIDC4        = "C4"
	xlsxCheckIDC5        = "C5"
	xlsxCheckIDC6        = "C6"
	xlsxCheckIDC7        = "C7"
	xlsxReasonMissingKey = "missing key"
	xlsxReasonUnexpKey   = "unexpected key"
	xlsxReasonDupKey     = "duplicate key"
	xlsxReasonNullValue  = "null value"
	xlsxReasonTypeMis    = "type mismatch"
	xlsxReasonNonInteger = "non-integer number"
	xlsxReasonNotObject  = "not an object"
	xlsxReasonNotAdd     = "action is not add"
	xlsxReasonMissing    = "missing in output"
	xlsxReasonNoValid    = "no valid line, caused by " + xlsxCheckIDC1 + "/" + xlsxCheckIDC2
	xlsxReasonNotSource  = "not in source"
	xlsxReasonValueMis   = "value mismatch"
	xlsxReasonDupFmt     = "duplicate, first line: %d"
	xlsxReasonCountMis   = "count mismatch"
	xlsxReasonPortRemove = "port removed"
)

const (
	xlsxReasonRequired      = "value is required"
	xlsxReasonPositiveInt   = "must be a positive integer"
	xlsxReasonNonNegInt     = "must be a non-negative integer"
	xlsxReasonMultiDomain   = "must contain a single domain"
	xlsxReasonInvalidPort   = "port suffix must be digits"
	xlsxReasonDomainChars   = "must contain only letters, digits, '.', '-' or '_'"
	xlsxReasonIDNameConfl   = "same cluster_id with different cluster_name"
	xlsxReasonNameIDConfl   = "same cluster_name with different cluster_id"
	xlsxReasonIDCloudConfl  = "same cluster_id with different bk_cloud_id"
	xlsxReasonSharedIndex   = "shared string index out of range"
	xlsxReasonInvalidRef    = "invalid cell reference"
	xlsxReasonSheetNotFound = "sheet relationship not found"
)

const xlsxReasonIntRange = "must not exceed 2147483647"

const xlsxDomainAllowedChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"

const (
	xlsxVerifyFileExt     = ".xlsx"
	xlsxVerifyNameSuffix  = "_cluster"
	xlsxVerifyStampDigits = 14
	xlsxVerifyInvalidInt  = -1
)

const (
	xlsxReasonMergeConfl   = "conflicts with merged row"
	xlsxReasonSrcDomainBad = "invalid domain in source"
)

const (
	errXlsxTemplateMutualExclusive = "--create-template-from-xlsx cannot be used with --create-template or " +
		"--create-template-from-list"
	errXlsxFileRequired        = "--xlsx-file is required"
	errXlsxOutputRequired      = "--create-template-from-xlsx is required"
	errXlsxNoDataRows          = "xlsx has no data rows"
	errXlsxHeaderRequired      = "xlsx header row is required"
	errXlsxMultipleSheetsFmt   = "xlsx must contain exactly one sheet, sheets: %s"
	errXlsxHiddenRowsFmt       = "xlsx has hidden rows, delete them before generating, rows: %s"
	errXlsxUnsupportedCellFmt  = "row: %d, column: %s, errmsg: unsupported cell type: %s"
	errXlsxVerifyFailedFmt     = "xlsx verify failed, report: %s"
	errXlsxPathConflictFmt     = "xlsx paths conflict, path: %s"
	errXlsxHeaderMissingFmt    = "xlsx header is missing, column: %s"
	errXlsxHeaderDuplicateFmt  = "xlsx header is duplicated, column: %s"
	errXlsxBkBizIDInvalid      = "--xlsx-bk-biz-id must be a positive integer"
	errXlsxBkBizIDFromNameFmt  = "cannot parse bk_biz_id from xlsx file name, file: %s, set --xlsx-bk-biz-id"
	errXlsxCellInvalidFmt      = "row: %d, column: %s, value: %q, errmsg: %s"
	errXlsxDuplicateConflFmt   = "row: %d, conflict row: %d, errmsg: %s"
	errXlsxRowInvalidFmt       = "row: %d, errmsg: %s"
	errXlsxOpenFmt             = "failed to open xlsx file, path: %s, errmsg: %s"
	errXlsxReadEntryFmt        = "failed to read xlsx entry, entry: %s, errmsg: %s"
	errXlsxEntryTooLargeFmt    = "xlsx entry is too large, entry: %s, limit: %d"
	errXlsxEntryMissingFmt     = "xlsx entry is missing, entry: %s"
	errXlsxParseEntryFmt       = "failed to parse xlsx entry, entry: %s, errmsg: %s"
	errXlsxWriteFileFmt        = "failed to write xlsx template, path: %s, errmsg: %s"
	errXlsxReadOutputFmt       = "failed to read xlsx template, path: %s, errmsg: %s"
	errXlsxWriteReportFmt      = "failed to write xlsx report, path: %s, errmsg: %s"
	errXlsxRenameFmt           = "failed to rename xlsx template, path: %s, errmsg: %s"
	errXlsxResolvePathFmt      = "failed to resolve xlsx path, path: %s, errmsg: %s"
	errXlsxValidateRecordFmt   = "row: %d, errmsg: %s"
	errXlsxSwitchVersionNeeded = "--xlsx-switch-version is required"
	errXlsxStatusNeeded        = "--xlsx-status is required"
)

const (
	xlsxWarnSwitchedByV2 = "imported clusters will be switched by v2 and skipped by v1"
	xlsxWarnNotVisible   = "records are not visible to whitelist query (requires v2 + enabled), " +
		"v1 keeps switching these clusters"
	xlsxWarnImportAdd = "add lines are imported without confirmation unless --upsert is set, run --dry-run first"
)

const (
	msgXlsxReportTitle       = "xlsx whitelist verify report\n"
	msgXlsxSourceFmt         = "source: %s\n"
	msgXlsxOutputFmt         = "output: %s\n"
	msgXlsxOutputKeptFmt     = "output: not updated, existing file kept: %s\n"
	msgXlsxOutputNotWritten  = "output: not written: %s\n"
	msgXlsxReportPathFmt     = "report: %s\n"
	msgXlsxBizFmt            = "bk_biz_id: %d, from: %s\n"
	msgXlsxParamsFmt         = "switch_version: %s, status: %s\n"
	msgXlsxRowsFmt           = "source_rows: %d, data_rows: %d, empty_rows: %d\n"
	msgXlsxLinesFmt          = "output_lines: %d, merged_duplicates: %d\n"
	msgXlsxChecksTitle       = "checks:\n"
	msgXlsxCheckFmt          = "  [%s] %s %s: %d/%d\n"
	msgXlsxCheckUniqueFmt    = "  [%s] %s %s: cluster_id %d, cluster_name %d\n"
	msgXlsxCheckCountPassFmt = "  [%s] %s %s: %d = %d + %d\n"
	msgXlsxCheckCountFailFmt = "  [%s] %s %s: %d != %d + %d\n"
	msgXlsxDetailFmt         = "    %s\n"
	msgXlsxMoreFmt           = "    ... more: %d\n"
	msgXlsxStatFmt           = "%s: %s\n"
	msgXlsxStatPairFmt       = "%s: %d"
	msgXlsxNormalizedFmt     = "normalized: %d\n"
	msgXlsxNormalizedItemFmt = "  row: %d, field: %s, xlsx: %s, json: %s, reason: %s\n"
	msgXlsxMergedTitle       = "merged:\n"
	msgXlsxMergedItemFmt     = "  row: %d, merged_into_row: %d, cluster_id: %d\n"
	msgXlsxWarningsTitle     = "warnings:\n"
	msgXlsxWarningItemFmt    = "  - %s\n"
	msgXlsxResultFmt         = "result: %s\n"
	msgXlsxDetailPairFmt     = "%s: %s"
	msgXlsxStatByCloud       = "by_bk_cloud_id"
	msgXlsxStatByType        = "by_cluster_type"
	msgXlsxStatByStatus      = "by_status"
	msgXlsxDetailRow         = "row"
	msgXlsxDetailLine        = "line"
	msgXlsxDetailClusterID   = "cluster_id"
	msgXlsxDetailField       = "field"
	msgXlsxDetailXlsx        = "xlsx"
	msgXlsxDetailExpected    = "expected"
	msgXlsxDetailJSON        = "json"
	msgXlsxDetailReason      = "reason"
)
