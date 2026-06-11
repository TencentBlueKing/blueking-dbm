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
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// Client represents the black-white list API client
type Client struct {
	baseURL    string
	token      string
	timeout    time.Duration
	httpClient *http.Client
	maxRetries int
	retryDelay time.Duration
}

// NewClient creates a new API client
func NewClient(baseURL, token string, timeout time.Duration) *Client {
	return &Client{
		baseURL:    baseURL,
		token:      token,
		timeout:    timeout,
		httpClient: &http.Client{Timeout: timeout},
		maxRetries: defaultMaxRetries,
		retryDelay: defaultRetryDelay,
	}
}

// GetBlackWhiteList retrieves black-white list entries with optional filters
func (c *Client) GetBlackWhiteList(bkCloudID int, queryArgs *GetBlackWhiteListRequest) ([]BlackWhiteListItem, error) {
	request := APIRequest{
		DbCloudToken: c.token,
		BkCloudID:    bkCloudID,
		Name:         apiNameGetBlackWhiteList,
		QueryArgs:    queryArgs,
	}

	var response GetListResponse
	err := c.doRequest(request, &response)
	if err != nil {
		return nil, err
	}

	if response.Code != httpStatusOKCode {
		return nil, gerrors.Newf(gerrors.Failure, errAPIFormat, response.Msg, response.Code)
	}

	return response.Data, nil
}

// InsertBlackWhiteList adds a new black-white list entry
func (c *Client) InsertBlackWhiteList(bkCloudID int, setArgs InsertBlackWhiteListRequest) (uint, error) {
	if err := setArgs.Validate(); err != nil {
		return 0, gerrors.Newf(gerrors.InvalidParameter, errInvalidInsertFormat, err)
	}

	request := APIRequest{
		DbCloudToken: c.token,
		BkCloudID:    bkCloudID,
		Name:         apiNameInsertBlackWhiteList,
		SetArgs:      setArgs,
	}

	var response InsertResponse
	err := c.doRequest(request, &response)
	if err != nil {
		return 0, err
	}

	if response.Code != httpStatusOKCode {
		return 0, gerrors.Newf(gerrors.Failure, errAPIFormat, response.Msg, response.Code)
	}

	return response.Data.ID, nil
}

// UpdateBlackWhiteList updates an existing black-white list entry
func (c *Client) UpdateBlackWhiteList(bkCloudID int, updateReq UpdateBlackWhiteListRequest) (int, error) {
	if err := updateReq.Validate(); err != nil {
		return 0, gerrors.Newf(gerrors.InvalidParameter, errInvalidUpdateFormat, err)
	}

	request := APIRequest{
		DbCloudToken: c.token,
		BkCloudID:    bkCloudID,
		Name:         apiNameUpdateBlackWhiteList,
		QueryArgs:    updateReq.QueryArgs,
		SetArgs:      updateReq.SetArgs,
	}

	var response UpdateResponse
	err := c.doRequest(request, &response)
	if err != nil {
		return 0, err
	}

	if response.Code != httpStatusOKCode {
		return 0, gerrors.Newf(gerrors.Failure, errAPIFormat, response.Msg, response.Code)
	}

	return response.Data.RowsAffected, nil
}

// DeleteBlackWhiteList deletes a black-white list entry
func (c *Client) DeleteBlackWhiteList(bkCloudID int, deleteReq DeleteBlackWhiteListRequest) (int, error) {
	if err := deleteReq.Validate(); err != nil {
		return 0, gerrors.Newf(gerrors.InvalidParameter, errInvalidDeleteFormat, err)
	}

	request := APIRequest{
		DbCloudToken: c.token,
		BkCloudID:    bkCloudID,
		Name:         apiNameDeleteBlackWhiteList,
		QueryArgs:    deleteReq,
	}

	var response DeleteResponse
	err := c.doRequest(request, &response)
	if err != nil {
		return 0, err
	}

	if response.Code != httpStatusOKCode {
		return 0, gerrors.Newf(gerrors.Failure, errAPIFormat, response.Msg, response.Code)
	}

	return response.Data.RowsAffected, nil
}

// doRequest performs the HTTP request with retry mechanism
func (c *Client) doRequest(request interface{}, response interface{}) error {
	var lastErr error

	for attempt := 1; attempt <= c.maxRetries; attempt++ {
		err := c.doSingleRequest(request, response)
		if err == nil {
			return nil
		}

		lastErr = err

		// Don't retry on client errors (4xx) or invalid parameters
		if c.shouldNotRetry(err) {
			break
		}

		if attempt < c.maxRetries {
			time.Sleep(c.retryDelay)
		}
	}

	return gerrors.Newf(gerrors.Failure, errRequestFailedFormat, c.maxRetries, lastErr)
}

// doSingleRequest performs a single HTTP request
func (c *Client) doSingleRequest(request interface{}, response interface{}) error {
	// Marshal request to JSON
	requestBody, err := json.Marshal(request)
	if err != nil {
		return gerrors.Newf(gerrors.InvalidJson, errMarshalRequestFormat, err)
	}

	// Create HTTP request
	req, err := http.NewRequest(httpMethodPost, c.baseURL, bytes.NewBuffer(requestBody))
	if err != nil {
		return gerrors.Newf(gerrors.NetException, errCreateRequestFormat, err)
	}

	req.Header.Set(httpHeaderContent, httpContentTypeJSON)

	// Execute request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return gerrors.Newf(gerrors.NetException, errHTTPRequestFormat, err)
	}
	defer resp.Body.Close()

	// Read response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return gerrors.Newf(gerrors.HttpRequestFailure, errReadResponseFormat, err)
	}

	// Check HTTP status code
	if resp.StatusCode != http.StatusOK {
		return gerrors.Newf(gerrors.Failure, errHTTPStatusFormat, resp.Status, string(body))
	}

	// Unmarshal response
	err = json.Unmarshal(body, response)
	if err != nil {
		return gerrors.Newf(gerrors.InvalidJson, errUnmarshalResponseFmt, err, string(body))
	}

	return nil
}

// shouldNotRetry determines if a request should not be retried
func (c *Client) shouldNotRetry(err error) bool {
	gerr, ok := err.(*gerrors.Error)
	if !ok {
		return false
	}

	// Don't retry on client errors (invalid parameters, JSON marshal failures).
	if gerr.HasCode(gerrors.InvalidParameter) || gerr.HasCode(gerrors.InvalidJson) {
		return true
	}

	// Check for HTTP 4xx errors (client errors) embedded in failure messages.
	if gerr.HasCode(gerrors.Failure) {
		errStr := err.Error()
		if contains(errStr, httpStatusBadRequest) || contains(errStr, httpStatusUnauthorized) ||
			contains(errStr, httpStatusForbidden) || contains(errStr, httpStatusNotFound) ||
			contains(errStr, httpStatusUnprocessableEntity) {
			return true
		}
	}

	return false
}

// contains checks if a string contains another string
func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && len(substr) > 0 &&
		bytes.Contains([]byte(s), []byte(substr)))
}

// SetMaxRetries sets the maximum number of retry attempts
func (c *Client) SetMaxRetries(maxRetries int) {
	if maxRetries > 0 {
		c.maxRetries = maxRetries
	}
}

// SetRetryDelay sets the delay between retry attempts
func (c *Client) SetRetryDelay(delay time.Duration) {
	if delay > 0 {
		c.retryDelay = delay
	}
}

// GetBaseURL returns the base URL of the client
func (c *Client) GetBaseURL() string {
	return c.baseURL
}

// GetTimeout returns the timeout duration of the client
func (c *Client) GetTimeout() time.Duration {
	return c.timeout
}
