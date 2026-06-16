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

// Package bwmgr defines the black-white list API client and request models.
package bwmgr

import "time"

const (
	apiNameGetBlackWhiteList    = "get_black_white_list"
	apiNameInsertBlackWhiteList = "insert_black_white_list"
	apiNameUpdateBlackWhiteList = "update_black_white_list"
	apiNameDeleteBlackWhiteList = "delete_black_white_list"
)

const (
	httpMethodPost      = "POST"
	httpHeaderContent   = "Content-Type"
	httpContentTypeJSON = "application/json"
	httpStatusOKCode    = 0
)

const (
	httpStatusBadRequest          = "400"
	httpStatusUnauthorized        = "401"
	httpStatusForbidden           = "403"
	httpStatusNotFound            = "404"
	httpStatusUnprocessableEntity = "422"
)

const (
	defaultMaxRetries = 3
	defaultRetryDelay = 2 * time.Second
)

const (
	errAPIFormat              = "API error: %s (code: %d)"
	errInvalidInsertFormat    = "invalid insert parameters: %v"
	errInvalidUpdateFormat    = "invalid update parameters: %v"
	errInvalidDeleteFormat    = "invalid delete parameters: %v"
	errRequestFailedFormat    = "request failed after %d attempts: %v"
	errMarshalRequestFormat   = "failed to marshal request: %v"
	errCreateRequestFormat    = "failed to create request: %v"
	errHTTPRequestFormat      = "HTTP request failed: %v"
	errReadResponseFormat     = "failed to read response: %v"
	errHTTPStatusFormat       = "HTTP error: %s, response: %s"
	errUnmarshalResponseFmt   = "failed to unmarshal response: %v, body: %s"
	errBkBizIDRequired        = "bk_biz_id is required and cannot be 0"
	errClusterIDRequired      = "cluster_id is required and cannot be 0"
	errClusterNameRequired    = "cluster_name is required"
	errSwitchVersionInvalid   = "switch_version must be either 'v1' or 'v2'"
	errStatusInvalid          = "status must be either 'enabled' or 'disabled'"
	errUpdateQueryArgsMissing = "at least one query argument (id, bk_biz_id, cluster_id, or " +
		"cluster_name) is required"
	errUpdateSetArgsMissing = "at least one set argument (cluster_name, switch_version, or status) is required"
	errDeleteArgsMissing    = "at least one argument (id, bk_biz_id, cluster_id, or cluster_name) is required"
)
