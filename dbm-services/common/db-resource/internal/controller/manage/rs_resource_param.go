/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package manage

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"

	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/logger"
)

// QueryResourceParamReq query resource operation parameter by bill_id or task_id
type QueryResourceParamReq struct {
	BillID string `json:"bill_id" binding:"omitempty,max=128"`
	TaskID string `json:"task_id" binding:"omitempty,max=128"`
	Latest bool   `json:"latest" binding:"omitempty"` // If true, only return the latest record
	Limit  int    `json:"limit" binding:"omitempty,min=1,max=1000"`
	Offset int    `json:"offset" binding:"omitempty,min=0"`
}

// Validate validate request parameters
func (req *QueryResourceParamReq) Validate() error {
	if req.BillID == "" && req.TaskID == "" {
		return fmt.Errorf("bill_id and task_id cannot both be empty")
	}
	// If latest is true, override limit to 1 to get only the most recent record
	if req.Latest {
		req.Limit = 1
		req.Offset = 0
	} else if req.Limit <= 0 {
		req.Limit = 100
	}
	return nil
}

// QueryResourceParamResp response for query resource operation parameter
type QueryResourceParamResp struct {
	RequestBodyList []map[string]interface{} `json:"request_body_list"`
}

// formatRequestBody format JSON string to proper JSON object
// Returns formatted JSON object and error if parsing fails
func formatRequestBody(jsonStr string) (map[string]interface{}, error) {
	if jsonStr == "" {
		return map[string]interface{}{}, nil
	}

	var result map[string]interface{}
	if err := json.Unmarshal([]byte(jsonStr), &result); err != nil {
		return nil, fmt.Errorf("failed to parse JSON: %w", err)
	}

	return result, nil
}

// formatRequestBodyList format a list of JSON strings to JSON objects
// Skips records that fail to parse and logs errors
func formatRequestBodyList(jsonStrs []string) []map[string]interface{} {
	result := make([]map[string]interface{}, 0, len(jsonStrs))
	for i, jsonStr := range jsonStrs {
		formatted, err := formatRequestBody(jsonStr)
		if err != nil {
			logger.Error("failed to parse request_body at index %d: %v, data: %s", i, err,
				maskSensitiveData(jsonStr))
			continue
		}
		result = append(result, formatted)
	}
	return result
}

// sensitiveFields list of sensitive field names to be masked
var sensitiveFields = []string{
	"password",
	"passwd",
	"pwd",
	"token",
	"authorization",
	"auth",
	"secret",
	"apikey",
	"api_key",
	"access_key",
	"secret_key",
	"private_key",
	"credential",
}

// maskSensitiveData mask sensitive data in JSON string for logging
func maskSensitiveData(jsonStr string) string {
	if jsonStr == "" {
		return ""
	}

	// Truncate to prevent large logs
	maxLen := 500
	if len(jsonStr) > maxLen {
		jsonStr = jsonStr[:maxLen] + "...[truncated]"
	}

	// Simple masking for common sensitive patterns
	lowerStr := strings.ToLower(jsonStr)
	for _, field := range sensitiveFields {
		if strings.Contains(lowerStr, field) {
			return "[CONTAINS_SENSITIVE_DATA]"
		}
	}

	return jsonStr
}

// redactSensitiveFields mask sensitive field values in a map
func redactSensitiveFields(data map[string]interface{}) map[string]interface{} {
	result := make(map[string]interface{})
	for k, v := range data {
		lowerKey := strings.ToLower(k)
		isSensitive := false
		for _, field := range sensitiveFields {
			if lowerKey == field {
				isSensitive = true
				break
			}
		}
		if isSensitive {
			result[k] = "***MASKED***"
		} else if nestedMap, ok := v.(map[string]interface{}); ok {
			result[k] = redactSensitiveFields(nestedMap)
		} else {
			result[k] = v
		}
	}
	return result
}

// MachineResourceParamHandler TODO
type MachineResourceParamHandler struct {
	controller.BaseHandler
}

// QueryResourceParam query resource operation parameters by bill_id or task_id
// POST /resource/param/query
func (h *MachineResourceParamHandler) QueryResourceParam(c *gin.Context) {
	// Set request timeout
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	// Limit request body size
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 1<<20) // 1MB

	// Parse and validate request parameters using Prepare
	var req QueryResourceParamReq
	if err := h.Prepare(c, &req); err != nil {
		return
	}

	// Custom validation
	if err := req.Validate(); err != nil {
		logger.Error("Validate Failed: %s", err.Error())
		h.SendResponse(c, err, nil)
		return
	}

	// Log request parameters (sensitive data is masked by Prepare)
	logger.Info("QueryResourceParam request: bill_id=%s, task_id=%s, latest=%v, limit=%d, offset=%d, request_id=%s",
		maskSensitiveData(req.BillID), maskSensitiveData(req.TaskID), req.Latest, req.Limit, req.Offset,
		c.GetString("request_id"))

	// Query database with context and timeout
	requestBodies, err := model.QueryResourceParamByBillOrTask(ctx, req.BillID, req.TaskID, req.Limit, req.Offset)
	if err != nil {
		logger.Error("QueryResourceParamByBillOrTask failed: %v, request_id=%s", err, c.GetString("request_id"))
		h.SendResponse(c, err, nil)
		return
	}

	// Format request bodies
	formattedList := formatRequestBodyList(requestBodies)

	// Redact sensitive fields in response
	for i, body := range formattedList {
		formattedList[i] = redactSensitiveFields(body)
	}

	// Log query results
	logger.Info("QueryResourceParam success: found %d records, request_id=%s", len(formattedList),
		c.GetString("request_id"))

	// Return response using SendResponse
	h.SendResponse(c, nil, QueryResourceParamResp{
		RequestBodyList: formattedList,
	})
}

// RegisterRouter register resource parameter query router
func (h *MachineResourceParamHandler) RegisterRouter(engine *gin.Engine) {
	r := engine.Group("resource")
	{
		r.POST("/param/query", h.QueryResourceParam)
	}
}
