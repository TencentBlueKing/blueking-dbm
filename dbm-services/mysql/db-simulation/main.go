/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package main

import (
	"bytes"
	"io"
	"net/http"
	"os"
	"time"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/model"
	"dbm-services/mysql/db-simulation/router"

	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"

	"github.com/gin-contrib/pprof"
	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
)

var buildstamp = ""
var githash = ""
var version = ""

func main() {
	app := gin.New()
	pprof.Register(app)

	// setup trace
	trace.Setup()
	// apm: add otlgin middleware
	app.Use(otelgin.Middleware("db_simulation"))
	// apm: add prom metrics middleware
	metric.NewPrometheus("").Use(app)

	app.Use(requestid.New())
	app.Use(apiLogger)
	router.RegisterRouter(app)
	app.POST("/app", func(ctx *gin.Context) {
		ctx.SecureJSON(http.StatusOK, map[string]interface{}{"buildstamp": buildstamp, "githash": githash,
			"version": version})
	})
	app.Run(config.GAppConfig.ListenAddr)
}

func init() {
	logger.New(os.Stdout, true, logger.InfoLevel, map[string]string{})
	defer logger.Sync()
}

// apiLogger TODO
func apiLogger(c *gin.Context) {
	rid := requestid.Get(c)
	c.Set("request_id", rid)
	var buf bytes.Buffer
	if c.Request.Method == http.MethodPost {
		tee := io.TeeReader(c.Request.Body, &buf)
		body, _ := io.ReadAll(tee)
		c.Request.Body = io.NopCloser(&buf)
		if len(body) <= 0 {
			body = []byte("{}")
		}
		model.DB.Create(&model.TbRequestRecord{
			RequestID:   rid,
			Method:      c.Request.Method,
			Path:        c.Request.URL.Path,
			SourceIP:    c.Request.RemoteAddr,
			RequestBody: string(body),
			CreateTime:  time.Now(),
			UpdateTime:  time.Now(),
		})
	}
	c.Next()
}
