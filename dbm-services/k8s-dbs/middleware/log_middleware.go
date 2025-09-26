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
		reqBody := ParseReqBody(c)
		// 劫持 ResponseWriter 以捕获响应内容
		writer := &DbsResponseWriter{body: bytes.NewBufferString(""), ResponseWriter: c.Writer}
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
			zap.Int64("latency_ms", commutil.GetLatencyMs(start)),
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
