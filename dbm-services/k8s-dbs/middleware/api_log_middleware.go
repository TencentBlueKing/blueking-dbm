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

package middleware

import (
	"bytes"
	"encoding/json"
	"log/slog"
	"time"

	commutil "k8s-dbs/common/util"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	commapi "k8s-dbs/common/api"
)

// IgnorePaths 忽略日志上报的 API 路径
var IgnorePaths = map[string]bool{
	"/metrics":       true,
	"/common/health": true,
}

// LogMiddleware 日志中间件
func LogMiddleware(logger *zap.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		// 过滤不需要指标上报的接口
		if skip := shouldSkipPath(c); skip {
			return
		}
		start := time.Now()
		requestedAt := commutil.Now(commutil.LayoutYYYYMMDDHHMMSS)
		reqBody := ParseReqBody(c)
		// 劫持 ResponseWriter 以捕获响应内容
		writer := &DbsResponseWriter{body: bytes.NewBufferString(""), ResponseWriter: c.Writer}
		c.Writer = writer
		c.Next()
		resBody := writer.body.Bytes()
		apiResponse, err := unMarshalResponse(resBody)
		if err != nil {
			slog.Error("failed to parse response bytes to apiResponse", "resBody", string(resBody), "err", err)
			return
		}

		logger.Info(apiResponse.Message,
			zap.String("requested_at", requestedAt),
			zap.String("method", c.Request.Method),
			zap.String("path", c.Request.URL.Path),
			zap.String("query", commutil.Truncate(c.Request.URL.RawQuery, 1024)),
			zap.Any("headers", c.Request.Header),
			zap.String("request_body", commutil.Truncate(string(reqBody), 1024)),
			zap.Int("status", c.Writer.Status()),
			zap.String("response_body", commutil.Truncate(string(resBody), 1024)),
			zap.Int64("result_code", int64(apiResponse.Code)),
			zap.Bool("result", apiResponse.Result),
			zap.Any("error", apiResponse.Error),
			zap.String("user_agent", c.Request.UserAgent()),
			zap.Int64("latency_ms", commutil.GetLatencyMs(start)),
		)
	}
}

// unMarshalResponse 反序列化获取 Response
func unMarshalResponse(respBytes []byte) (*commapi.Response, error) {
	var response commapi.Response
	if err := json.Unmarshal(respBytes, &response); err != nil {
		slog.Error("failed to unmarshal response bytes", "resBody", string(respBytes), "err", err)
		return nil, err
	}
	return &response, nil
}

// shouldSkip 是否忽略日志上报
func shouldSkipPath(c *gin.Context) bool {
	path := c.Request.URL.Path
	if IgnorePaths[path] {
		slog.Warn("当前接口路径不需要进行日志上报", "接口路径", path)
		return true
	}
	return false
}
