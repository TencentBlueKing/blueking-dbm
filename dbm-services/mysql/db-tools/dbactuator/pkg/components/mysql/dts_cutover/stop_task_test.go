/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package dts_cutover

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

func TestStopTaskWhileLockedSendsShortTimeoutAndReturnsOnHTTPError(t *testing.T) {
	var got StopTaskRequest
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.Equal(t, http.MethodPost, r.Method)
		require.Equal(t, "/api/v1/tasks/task-a/stop", r.URL.Path)
		require.NoError(t, json.NewDecoder(r.Body).Decode(&got))
		http.Error(w, "stop failed", http.StatusInternalServerError)
	}))
	defer srv.Close()

	start := time.Now()
	err := StopTaskWhileLocked(srv.URL, "task-a")
	require.Error(t, err)
	require.Contains(t, err.Error(), "HTTP 500")
	require.Equal(t, "15s", got.TimeoutDuration)
	require.Less(t, time.Since(start), time.Second)
}

func TestStopTaskWhileLockedSuccess(t *testing.T) {
	var got StopTaskRequest
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.NoError(t, json.NewDecoder(r.Body).Decode(&got))
		w.WriteHeader(http.StatusOK)
		_, writeErr := w.Write([]byte(`{"result":true}`))
		require.NoError(t, writeErr)
	}))
	defer srv.Close()

	require.NoError(t, StopTaskWhileLocked(srv.URL, "task-a"))
	require.Equal(t, "15s", got.TimeoutDuration)
}

func TestDoStopTaskClientTimeoutReturnsWithoutWaitingOutServer(t *testing.T) {
	release := make(chan struct{})
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		<-release
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()
	defer close(release)

	start := time.Now()
	err := doStopTask(srv.URL, "task-a", 200*time.Millisecond, &StopTaskRequest{
		TimeoutDuration: "15s",
	})
	elapsed := time.Since(start)
	require.Error(t, err)
	require.Contains(t, err.Error(), "停止任务 API 调用失败")
	require.Less(t, elapsed, time.Second)
}
