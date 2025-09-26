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
	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"io"
	dbslogger "k8s-dbs/logger"
	"log/slog"

	"github.com/gin-gonic/gin"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
)

// RegisterMiddleWare 注册 MiddleWave
func RegisterMiddleWare(engine *gin.Engine) {
	// 注册 logger 中间件
	dbsLogger := dbslogger.InitLogger()
	engine.Use(LogMiddleware(dbsLogger))
	slog.Info("Finish initial logger...")

	// 注册 trace 中间件
	// setup trace
	trace.Setup()
	// apm: add otlgin middleware
	engine.Use(otelgin.Middleware("k8s_dbs"))
	// apm: add prom metrics middleware
	metric.NewPrometheus("").Use(engine)
	slog.Info("Finish initial trace...")

	// 注册 metrics 中间件
	engine.Use(MetricsMiddleware())
	slog.Info("Finish initial metric...")
}

// ParseReqBody 获取请求消息体
func ParseReqBody(c *gin.Context) []byte {
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
	return reqBody
}

// DbsResponseWriter 用于捕获 Gin 的响应内容
type DbsResponseWriter struct {
	gin.ResponseWriter
	body *bytes.Buffer
}

func (d *DbsResponseWriter) Write(b []byte) (int, error) {
	d.body.Write(b)                  // 捕获响应内容
	return d.ResponseWriter.Write(b) // 正常写入响应
}
