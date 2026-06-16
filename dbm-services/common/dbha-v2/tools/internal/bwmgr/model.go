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

package bwmgr

import (
	"errors"
	"time"
)

// SwitchVersionType defines the type of switch version.
type SwitchVersionType string

const (
	SwitchVersionV1 SwitchVersionType = "v1"
	SwitchVersionV2 SwitchVersionType = "v2"
)

func (s SwitchVersionType) String() string {
	return string(s)
}

// StatusType defines the status type.
type StatusType string

const (
	StatusEnabled  StatusType = "enabled"
	StatusDisabled StatusType = "disabled"
)

func (s StatusType) String() string {
	return string(s)
}

// BlackWhiteListItem represents a single black-white list entry
// This matches the t_db_black_white_list table structure
// and the API response format
type BlackWhiteListItem struct {
	ID            uint              `json:"id"`
	BkBizID       int               `json:"bk_biz_id"`
	BkCloudID     int               `json:"bk_cloud_id"`
	ClusterID     int               `json:"cluster_id"`
	ClusterName   string            `json:"cluster_name"`
	SwitchVersion SwitchVersionType `json:"switch_version"`
	Status        StatusType        `json:"status"`
	CreatedAt     time.Time         `json:"created_at"`
	UpdatedAt     time.Time         `json:"updated_at"`
}

// GetBlackWhiteListRequest represents the request for getting black-white list
// This matches the API query_args structure
type GetBlackWhiteListRequest struct {
	BkBizID       *int               `json:"bk_biz_id,omitempty"`
	BkCloudID     *int               `json:"bk_cloud_id,omitempty"`
	ClusterID     *int               `json:"cluster_id,omitempty"`
	ClusterName   *string            `json:"cluster_name,omitempty"`
	SwitchVersion *SwitchVersionType `json:"switch_version,omitempty"`
	Status        *StatusType        `json:"status,omitempty"`
}

// InsertBlackWhiteListRequest represents the request for inserting a new entry
// This matches the API set_args structure for insert operation
type InsertBlackWhiteListRequest struct {
	BkBizID       int               `json:"bk_biz_id"`
	BkCloudID     int               `json:"bk_cloud_id"`
	ClusterID     int               `json:"cluster_id"`
	ClusterName   string            `json:"cluster_name"`
	SwitchVersion SwitchVersionType `json:"switch_version"`
	Status        StatusType        `json:"status,omitempty"`
}

// UpdateBlackWhiteListRequest represents the request for updating an entry
// Contains both query_args for locating the entry and set_args for updating
type UpdateBlackWhiteListRequest struct {
	QueryArgs UpdateQueryArgs `json:"query_args"`
	SetArgs   UpdateSetArgs   `json:"set_args"`
}

// UpdateQueryArgs represents the query arguments for update operation
type UpdateQueryArgs struct {
	ID          *uint   `json:"id,omitempty"`
	BkBizID     *int    `json:"bk_biz_id,omitempty"`
	BkCloudID   *int    `json:"bk_cloud_id,omitempty"`
	ClusterID   *int    `json:"cluster_id,omitempty"`
	ClusterName *string `json:"cluster_name,omitempty"`
}

// UpdateSetArgs represents the set arguments for update operation
type UpdateSetArgs struct {
	ClusterName   *string            `json:"cluster_name,omitempty"`
	SwitchVersion *SwitchVersionType `json:"switch_version,omitempty"`
	Status        *StatusType        `json:"status,omitempty"`
}

// DeleteBlackWhiteListRequest represents the request for deleting an entry
type DeleteBlackWhiteListRequest struct {
	ID          *uint   `json:"id,omitempty"`
	BkBizID     *int    `json:"bk_biz_id,omitempty"`
	BkCloudID   *int    `json:"bk_cloud_id,omitempty"`
	ClusterID   *int    `json:"cluster_id,omitempty"`
	ClusterName *string `json:"cluster_name,omitempty"`
}

// APIRequest represents the generic API request structure
type APIRequest struct {
	DbCloudToken string      `json:"db_cloud_token"`
	BkCloudID    int         `json:"bk_cloud_id"`
	Name         string      `json:"name"`
	QueryArgs    interface{} `json:"query_args,omitempty"`
	SetArgs      interface{} `json:"set_args,omitempty"`
}

// APIResponse represents the generic API response structure
type APIResponse struct {
	Code int         `json:"code"`
	Msg  string      `json:"msg"`
	Data interface{} `json:"data"`
}

// GetListResponse represents the response for get_black_white_list API
type GetListResponse struct {
	Code int                  `json:"code"`
	Msg  string               `json:"msg"`
	Data []BlackWhiteListItem `json:"data"`
}

// InsertResponse represents the response for insert_black_white_list API
type InsertResponse struct {
	Code int        `json:"code"`
	Msg  string     `json:"msg"`
	Data InsertData `json:"data"`
}

// InsertData represents insert_black_white_list response data.
type InsertData struct {
	ID           uint `json:"id"`
	RowsAffected int  `json:"rowsAffected"`
}

// UpdateResponse represents the response for update_black_white_list API
type UpdateResponse struct {
	Code int        `json:"code"`
	Msg  string     `json:"msg"`
	Data UpdateData `json:"data"`
}

// UpdateData represents update_black_white_list response data.
type UpdateData struct {
	RowsAffected int `json:"rowsAffected"`
}

// DeleteResponse represents the response for delete_black_white_list API
type DeleteResponse struct {
	Code int        `json:"code"`
	Msg  string     `json:"msg"`
	Data DeleteData `json:"data"`
}

// DeleteData represents delete_black_white_list response data.
type DeleteData struct {
	RowsAffected int `json:"rowsAffected"`
}

// Validate validates the insert request parameters.
func (r *InsertBlackWhiteListRequest) Validate() error {
	if r.BkBizID == 0 {
		return errors.New(errBkBizIDRequired)
	}

	if r.ClusterID == 0 {
		return errors.New(errClusterIDRequired)
	}

	if r.ClusterName == "" {
		return errors.New(errClusterNameRequired)
	}

	if r.SwitchVersion != SwitchVersionV1 && r.SwitchVersion != SwitchVersionV2 {
		return errors.New(errSwitchVersionInvalid)
	}

	if r.Status != "" && r.Status != StatusEnabled && r.Status != StatusDisabled {
		return errors.New(errStatusInvalid)
	}

	return nil
}

// Validate validates the update request parameters.
func (r *UpdateBlackWhiteListRequest) Validate() error {
	// Check if at least one query argument is provided
	if r.QueryArgs.ID == nil && r.QueryArgs.BkBizID == nil &&
		r.QueryArgs.ClusterID == nil && r.QueryArgs.ClusterName == nil {
		return errors.New(errUpdateQueryArgsMissing)
	}

	// Check if at least one set argument is provided
	if r.SetArgs.ClusterName == nil && r.SetArgs.SwitchVersion == nil && r.SetArgs.Status == nil {
		return errors.New(errUpdateSetArgsMissing)
	}

	// Validate switch_version if provided
	if r.SetArgs.SwitchVersion != nil &&
		*r.SetArgs.SwitchVersion != SwitchVersionV1 && *r.SetArgs.SwitchVersion != SwitchVersionV2 {
		return errors.New(errSwitchVersionInvalid)
	}

	// Validate status if provided
	if r.SetArgs.Status != nil &&
		*r.SetArgs.Status != StatusEnabled && *r.SetArgs.Status != StatusDisabled {
		return errors.New(errStatusInvalid)
	}

	return nil
}

// Validate validates the delete request parameters.
func (r *DeleteBlackWhiteListRequest) Validate() error {
	// Check if at least one argument is provided
	if r.ID == nil && r.BkBizID == nil &&
		r.ClusterID == nil && r.ClusterName == nil {
		return errors.New(errDeleteArgsMissing)
	}

	return nil
}
