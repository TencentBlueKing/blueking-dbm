/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cc

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"time"

	"github.com/google/go-querystring/query"
)

const (
	// apiserver response code
	statusSuccess int = 0
)

// Response TODO
type Response struct {
	Code       int             `json:"code"`
	Permission json.RawMessage `json:"permission"`
	Result     bool            `json:"result"`
	RequestId  string          `json:"request_id"`
	Message    string          `json:"message"`
	Data       json.RawMessage `json:"data"`
	Error      json.RawMessage `json:"error"`
}

// Client TODO
type Client struct {
	apiserver string
	// client for apiservers
	client *http.Client
	// Blueking secret
	secret       Secret
	secretHeader string

	timeout time.Duration
}

// Secret TODO
type Secret struct {
	BKAppCode   string `json:"bk_app_code"`
	BKAppSecret string `json:"bk_app_secret"`
	BKUsername  string `json:"bk_username"`
}

// NewClient return new client
func NewClient(apiserver string, secret Secret) (*Client, error) {
	b, err := json.Marshal(secret)
	if err != nil {
		return nil, err
	}
	cli := &Client{
		apiserver:    apiserver,
		secret:       secret,
		secretHeader: string(b),
	}
	tr := &http.Transport{}
	cli.client = &http.Client{
		Transport: tr,
	}
	return cli, nil
}

// Timeout TODO
func (c *Client) Timeout(duration time.Duration) {
	c.timeout = duration
}

// Do main handler
func (c *Client) Do(method, uri string, params interface{}) (result *Response, err error) {
	var fullURL string
	body, err := json.Marshal(params)
	if err != nil {
		return nil, fmt.Errorf("RequestErr - %v", err)
	}
	if fullURL, err = url.JoinPath(c.apiserver, uri); err != nil {
		return nil, err
	}
	log.Println(fullURL, string(body))
	req, err := http.NewRequest(method, fullURL, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("RequestErr - new request failed: %v", err)
	}
	if c.timeout != 0 {
		ctx, cancel := context.WithTimeout(req.Context(), c.timeout)
		defer cancel()

		req = req.WithContext(ctx)
	}
	// Set Header

	req.Header.Set("X-Bkapi-Accept-Code-Type", "int")
	req.Header.Set("X-Bkapi-Authorization", c.secretHeader)

	if method == "GET" {
		q, _ := query.Values(params)
		log.Println("encode: ", q.Encode())
		req.URL.RawQuery = q.Encode()
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, err
	}

	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HttpCodeErr - Code: %v, Response: %+v", resp.StatusCode, resp)
	}
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("HttpCodeErr - Code: %v, io read all failed %s", resp.StatusCode, err.Error())
	}
	result = &Response{}
	err = json.Unmarshal(b, result)
	if err != nil {
		return nil, err
	}
	// check response and data is nil
	if result.Code != statusSuccess {
		return nil, fmt.Errorf("RequestErr - RequestId: %s, Code: %v,  Messag: %v, Error: %v",
			result.RequestId,
			result.Code,
			result.Message,
			string(result.Error))
	}
	return result, nil
}
