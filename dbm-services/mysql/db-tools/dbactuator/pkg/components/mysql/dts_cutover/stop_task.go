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
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// StopTaskRequest POST /api/v1/tasks/{task}/stop 请求体（与 OpenAPI 对齐）。
type StopTaskRequest struct {
	SourceNameList  []string `json:"source_name_list,omitempty"`
	TimeoutDuration string   `json:"timeout_duration,omitempty"`
}

// StopTask 调用 Master HTTP API 停止任务（与 status 查询同一通道，不走 dmctl）。
// POST http://{dts_master_addr}/api/v1/tasks/{task_name}/stop
func StopTask(dtsMasterAddr, taskName string, timeoutSec int, reqBody *StopTaskRequest) error {
	if timeoutSec <= 0 {
		timeoutSec = 600
	}
	u, err := buildMasterAPIURL(dtsMasterAddr, fmt.Sprintf("/api/v1/tasks/%s/stop", url.PathEscape(taskName)))
	if err != nil {
		return err
	}

	var bodyReader io.Reader
	if reqBody != nil {
		raw, mErr := json.Marshal(reqBody)
		if mErr != nil {
			return fmt.Errorf("序列化 stop 请求失败: %w", mErr)
		}
		bodyReader = bytes.NewReader(raw)
	} else {
		bodyReader = bytes.NewReader([]byte("{}"))
	}

	client := &http.Client{Timeout: time.Duration(timeoutSec) * time.Second}
	req, err := http.NewRequest(http.MethodPost, u, bodyReader)
	if err != nil {
		return fmt.Errorf("构造 stop 请求失败: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	logger.Info("调用 DTS API 停止任务: POST %s (timeout=%ds)", u, timeoutSec)
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("停止任务 API 调用失败: %w", err)
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf(
			"停止任务 API 失败: HTTP %d, body=%s",
			resp.StatusCode,
			truncateOut(string(respBody)),
		)
	}
	logger.Info("停止任务 API 成功: HTTP %d body=%s", resp.StatusCode, truncateOut(string(respBody)))
	return nil
}

func truncateOut(s string) string {
	const max = 2048
	if len(s) <= max {
		return s
	}
	return s[:max] + "...(truncated)"
}
