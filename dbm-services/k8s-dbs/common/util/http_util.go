/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package util

import (
	"encoding/json"
	"time"

	"github.com/go-resty/resty/v2"
	"github.com/pkg/errors"
)

const (
	DefaultTimeout       = 30 * time.Second
	DefaultRetry         = 3
	DefaultRetryWaitTime = 3 * time.Second
)

// HTTPClient http 客户端
type HTTPClient struct {
	client *resty.Client
}

var BaseHTTPClient *HTTPClient

// InitGlobalHTTPClient 初始化 BaseHTTPClient
func InitGlobalHTTPClient() {
	BaseHTTPClient = &HTTPClient{
		client: resty.New(),
	}
	BaseHTTPClient.client.SetTimeout(DefaultTimeout)
	BaseHTTPClient.client.SetRetryCount(DefaultRetry)
	BaseHTTPClient.client.SetRetryWaitTime(DefaultRetryWaitTime)
}

// Get 发送GET请求
func (c *HTTPClient) Get(url string) ([]byte, error) {
	response, err := c.client.R().Get(url)
	if err != nil {
		return nil, err
	}
	return response.Body(), nil
}

// GetWithResponse 发送GET请求并返回完整响应
func (c *HTTPClient) GetWithResponse(url string) (*resty.Response, error) {
	return c.client.R().Get(url)
}

// Post 发送POST请求(JSON数据)
func (c *HTTPClient) Post(url string, body interface{}) ([]byte, error) {
	response, err := c.client.R().
		SetHeader("Content-Type", "application/json").
		SetBody(body).
		Post(url)
	if err != nil {
		return nil, err
	}
	return response.Body(), nil
}

// PostWithResponse 发送POST请求(JSON数据)并返回完整响应
func (c *HTTPClient) PostWithResponse(url string, body interface{}) (*resty.Response, error) {
	return c.client.R().
		SetHeader("Content-Type", "application/json").
		SetBody(body).
		Post(url)
}

// Put 发送PUT请求(JSON数据)
func (c *HTTPClient) Put(url string, body interface{}) ([]byte, error) {
	response, err := c.client.R().
		SetHeader("Content-Type", "application/json").
		SetBody(body).
		Put(url)
	if err != nil {
		return nil, err
	}
	return response.Body(), nil
}

// PutWithResponse 发送PUT请求(JSON数据)并返回完整响应
func (c *HTTPClient) PutWithResponse(url string, body interface{}) (*resty.Response, error) {
	return c.client.R().
		SetHeader("Content-Type", "application/json").
		SetBody(body).
		Put(url)
}

// Delete 发送DELETE请求
func (c *HTTPClient) Delete(url string) ([]byte, error) {
	response, err := c.client.R().Delete(url)
	if err != nil {
		return nil, err
	}
	return response.Body(), nil
}

// DeleteWithResponse 发送DELETE请求并返回完整响应
func (c *HTTPClient) DeleteWithResponse(url string) (*resty.Response, error) {
	return c.client.R().Delete(url)
}

// PostForm 发送POST表单请求
func (c *HTTPClient) PostForm(url string, formData map[string]string) ([]byte, error) {
	response, err := c.client.R().
		SetHeader("Content-Type", "application/x-www-form-urlencoded").
		SetFormData(formData).
		Post(url)
	if err != nil {
		return nil, err
	}
	return response.Body(), nil
}

// PostFormWithResponse 发送POST表单请求并返回完整响应
func (c *HTTPClient) PostFormWithResponse(url string, formData map[string]string) (*resty.Response, error) {
	return c.client.R().
		SetHeader("Content-Type", "application/x-www-form-urlencoded").
		SetFormData(formData).
		Post(url)
}

// ParseResponse 解析响应到指定结构体
func (c *HTTPClient) ParseResponse(response *resty.Response, v interface{}) error {
	if response.IsError() {
		return errors.New(response.String())
	}
	return json.Unmarshal(response.Body(), v)
}

func init() {
	InitGlobalHTTPClient()
}
