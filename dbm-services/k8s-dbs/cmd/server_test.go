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

package main

import (
	"k8s-dbs/router"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestWebconsoleRetired(t *testing.T) {
	engine := gin.New()
	router.BuildRouter(engine, nil)

	const terminalPath = "/v4/dbs/webconsole"
	const query = "?k8sClusterName=test-k8s&namespace=test-ns&podName=test-pod&clusterName=test-cluster"
	tests := []struct {
		name    string
		query   string
		upgrade bool
	}{
		{name: "http_without_params"},
		{name: "http_with_params", query: query},
		{name: "websocket_without_params", upgrade: true},
		{name: "websocket_with_params", query: query, upgrade: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			request := httptest.NewRequest(http.MethodGet, terminalPath+tt.query, nil)
			if tt.upgrade {
				request.Header.Set("Connection", "Upgrade")
				request.Header.Set("Upgrade", "websocket")
				request.Header.Set("Sec-WebSocket-Version", "13")
				request.Header.Set("Sec-WebSocket-Key", "dGhlIHNhbXBsZSBub25jZQ==")
				request.Header.Set("Origin", "https://untrusted.example")
			}
			response := httptest.NewRecorder()
			engine.ServeHTTP(response, request)
			if response.Code != http.StatusGone {
				t.Errorf("expected status %d, got %d", http.StatusGone, response.Code)
			}
			if response.Header().Get("Upgrade") != "" || response.Header().Get("Sec-WebSocket-Accept") != "" {
				t.Error("retired terminal must not return WebSocket upgrade headers")
			}
		})
	}
}
