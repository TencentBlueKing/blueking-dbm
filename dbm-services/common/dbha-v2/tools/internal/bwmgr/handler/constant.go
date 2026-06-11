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
	jsonIndentPrefix = ""
	jsonIndentValue  = "  "
)

const (
	errSwitchVersionInvalid = "switch-version must be 'v1' or 'v2'"
	errStatusInvalid        = "status must be 'enabled' or 'disabled'"
	errGetListFormat        = "failed to get black-white list: %v"
	errFormatOutputFormat   = "failed to format output: %v"
	errBkBizIDRequired      = "bk-biz-id is required"
	errClusterIDRequired    = "cluster-id is required"
	errClusterNameRequired  = "cluster-name is required"
	errAddEntryFormat       = "failed to add black-white list entry: %v"
	errUpdateQueryRequired  = "at least one query parameter (id, bk-biz-id, cluster-id, or " +
		"cluster-name) is required"
	errUpdateSetRequired   = "at least one set parameter (switch-version or status) is required"
	errUpdateCancelled     = "update operation cancelled by user"
	errUpdateEntryFormat   = "failed to update black-white list entry: %v"
	errDeleteParamRequired = "at least one parameter (id, bk-biz-id, cluster-id, or " +
		"cluster-name) is required"
	errDeleteCancelled   = "delete operation cancelled by user"
	errDeleteEntryFormat = "failed to delete black-white list entry: %v"
)

const (
	msgAddSuccessFormat    = "Successfully added black-white list entry with ID: %d\n"
	msgUpdateSuccessFormat = "Successfully updated %d black-white list entry(ies)\n"
	msgDeleteSuccessFormat = "Successfully deleted %d black-white list entry(ies)\n"
)

const (
	warnUpdateRisky = "WARNING: this update may disable v2 white-listing and " +
		"affect ha-module(v1) switching behavior. Continue?"
	warnDeleteRisky = "WARNING: this will permanently delete the matched " +
		"black-white list entry(ies). Continue?"
)
