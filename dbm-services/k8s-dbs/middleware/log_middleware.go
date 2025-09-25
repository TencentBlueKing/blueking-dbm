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
	"io"
	"time"

	commutil "k8s-dbs/common/util"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	commapi "k8s-dbs/common/api"
)

// LogMiddleware 日志中间件
func LogMiddleware(logger *zap.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		var reqBody []byte
		if c.Request.Body != nil {
			// 复制一份请求体，因为 c.Request.Body 只能读取一次
			reqBodyBytes, err := io.ReadAll(c.Request.Body)
			if err == nil {
				reqBody = reqBodyBytes
				// 恢复请求体，以便后续 handler 正常读取
				c.Request.Body = io.NopCloser(bytes.NewBuffer(reqBodyBytes))
			}
		}

		// 劫持 ResponseWriter 以捕获响应内容
		writer := &responseWriter{body: bytes.NewBufferString(""), ResponseWriter: c.Writer}
		c.Writer = writer

		c.Next()

		resBody := writer.body.Bytes()

		logger.Info(getResponseMsg(resBody),
			zap.String("method", c.Request.Method),
			zap.String("path", c.Request.URL.Path),
			zap.String("query", commutil.Truncate(c.Request.URL.RawQuery, 1024)),
			zap.Any("headers", c.Request.Header),

			zap.String("request_body", commutil.Truncate(string(reqBody), 1024)),
			zap.Int("status", c.Writer.Status()),
			zap.String("response_body", commutil.Truncate(string(resBody), 1024)),
			zap.Int64("latency_ms", getLatencyMs(start)),
		)
	}
}

func getResponseMsg(respBytes []byte) string {
	var message = ""
	var response commapi.Response
	err := json.Unmarshal(respBytes, &response)
	if err == nil {
		message = response.Message
	}
	return message
}

func getLatencyMs(start time.Time) int64 {
	latency := time.Since(start)
	latencyMs := latency.Milliseconds()
	if latencyMs < 1 {
		latencyMs = 1
	}
	return latencyMs
}

// responseWriter 用于捕获 Gin 的响应内容
type responseWriter struct {
	gin.ResponseWriter
	body *bytes.Buffer
}

func (w *responseWriter) Write(b []byte) (int, error) {
	w.body.Write(b)                  // 捕获响应内容
	return w.ResponseWriter.Write(b) // 正常写入响应
}
