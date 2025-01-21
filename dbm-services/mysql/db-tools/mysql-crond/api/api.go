/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package api TODO
package api

import (
	"errors"
	"net/http"
)

// Manager TODO
type Manager struct {
	apiUrl string
	client *http.Client
}

// NewManager TODO
func NewManager(apiUrl string) *Manager {
	return &Manager{
		apiUrl: apiUrl,
		client: &http.Client{},
	}
}

// NotFoundError entry not found
var NotFoundError = errors.New("not found")

const (
	JobStatusEnabled  = "enabled"
	JobStatusDisabled = "disabled"
	JobStatusAll      = "all"
)

// JobStatusAllowed allowed
var JobStatusAllowed = []string{JobStatusEnabled, JobStatusDisabled, JobStatusAll}

// Resp client response
type Resp struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// NewErrorResp init
func NewErrorResp(code int, err error) *Resp {
	resp := &Resp{Code: code}
	if err != nil {
		resp.Message = err.Error()
	}
	return resp
}
