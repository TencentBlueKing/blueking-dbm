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
	"net/http"
	"net/url"
	"time"

	"dbm-services/common/go-pubpkg/logger"

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
	logger.Info("创建 CC API 客户端, apiserver: %s, bk_app_code: %s, bk_username: %s",
		apiserver, secret.BKAppCode, secret.BKUsername)

	b, err := json.Marshal(secret)
	if err != nil {
		logger.Error("CC API 客户端密钥序列化失败: %v", err)
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

	logger.Info("CC API 客户端创建成功, apiserver: %s", apiserver)
	return cli, nil
}

// Timeout TODO
func (c *Client) Timeout(duration time.Duration) {
	c.timeout = duration
	logger.Info("CC API 客户端设置超时, apiserver: %s, timeout: %v", c.apiserver, duration)
}

// Do main handler
func (c *Client) Do(method, uri string, params interface{}) (result *Response, err error) {
	startTime := time.Now()
	logger.Info("CC API 请求开始, method: %s, uri: %s, apiserver: %s", method, uri, c.apiserver)

	var fullURL string
	body, err := json.Marshal(params)
	if err != nil {
		logger.Error("CC API 参数序列化失败: %v", err)
		return nil, fmt.Errorf("RequestErr - %v", err)
	}

	if fullURL, err = url.JoinPath(c.apiserver, uri); err != nil {
		logger.Error("CC API URL 构建失败, apiserver: %s, uri: %s, error: %v", c.apiserver, uri, err)
		return nil, err
	}

	logger.Info("CC API 请求详情, fullURL: %s, method: %s, body: %s, timeout: %v",
		fullURL, method, string(body), c.timeout)

	req, err := http.NewRequest(method, fullURL, bytes.NewReader(body))
	if err != nil {
		logger.Error("CC API 创建请求失败: %v", err)
		return nil, fmt.Errorf("RequestErr - new request failed: %v", err)
	}

	if c.timeout != 0 {
		ctx, cancel := context.WithTimeout(req.Context(), c.timeout)
		defer cancel()
		req = req.WithContext(ctx)
		logger.Debug("CC API 设置请求超时, timeout: %v", c.timeout)
	}

	// Set Header
	req.Header.Set("X-Bkapi-Accept-Code-Type", "int")
	req.Header.Set("X-Bkapi-Authorization", c.secretHeader)
	req.Header.Set("Content-Type", "application/json")

	if method == "GET" {
		q, _ := query.Values(params)
		req.URL.RawQuery = q.Encode()
		logger.Debug("CC API GET 请求查询参数, query: %s", q.Encode())
	}

	logger.Debug("CC API 发送请求, url: %s, headers: %+v", req.URL.String(), req.Header)

	resp, err := c.client.Do(req)
	if err != nil {
		logger.Error("CC API 请求执行失败, url: %s, duration: %v, error: %v",
			req.URL.String(), time.Since(startTime), err)
		return nil, err
	}

	defer resp.Body.Close()

	logger.Info("CC API 收到响应, url: %s, status_code: %d, duration: %v",
		req.URL.String(), resp.StatusCode, time.Since(startTime))

	if resp.StatusCode != http.StatusOK {
		logger.Error("CC API 响应状态码异常, url: %s, status_code: %d, duration: %v",
			req.URL.String(), resp.StatusCode, time.Since(startTime))
		return nil, fmt.Errorf("HttpCodeErr - Code: %v, Response: %+v", resp.StatusCode, resp)
	}

	b, err := io.ReadAll(resp.Body)
	if err != nil {
		logger.Error("CC API 读取响应体失败, url: %s, status_code: %d, error: %v",
			req.URL.String(), resp.StatusCode, err)
		return nil, fmt.Errorf("HttpCodeErr - Code: %v, io read all failed %s", resp.StatusCode, err.Error())
	}

	logger.Debug("CC API 响应体, url: %s, response_body: %s", req.URL.String(), string(b))

	result = &Response{}
	err = json.Unmarshal(b, result)
	if err != nil {
		logger.Error("CC API 响应反序列化失败, url: %s, response_body: %s, error: %v",
			req.URL.String(), string(b), err)
		return nil, err
	}

	// check response and data is nil
	if result.Code != statusSuccess {
		logger.Error("CC API 业务逻辑错误, url: %s, request_id: %s, code: %d, Message: %s, error: %s, duration: %v",
			req.URL.String(), result.RequestId, result.Code, result.Message, string(result.Error), time.Since(startTime))
		return nil, fmt.Errorf("RequestErr - RequestId: %s, Code: %v,  Message: %v, Error: %v",
			result.RequestId, result.Code, result.Message, string(result.Error))
	}

	return result, nil
}
