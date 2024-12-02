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
	"context"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-contrib/pprof"
	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
	"github.com/samber/lo"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"

	_ "go.uber.org/automaxprocs"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/config"
	"dbm-services/mysql/db-simulation/handler"
	"dbm-services/mysql/db-simulation/model"
	"dbm-services/mysql/db-simulation/router"
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
	app.Use(returnRessponeMiddleware)
	router.RegisterRouter(app)
	app.POST("/app", func(ctx *gin.Context) {
		ctx.SecureJSON(http.StatusOK, map[string]interface{}{"buildstamp": buildstamp, "githash": githash,
			"version": version})
	})

	srv := &http.Server{
		Addr:              config.GAppConfig.ListenAddr,
		Handler:           app,
		ReadHeaderTimeout: 5 * time.Second,
	}
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("listen: %s\n", err)
		}
	}()
	// Wait for interrupt signal to gracefully shutdown the server with
	// a timeout of 5 seconds.
	quit := make(chan os.Signal, 1)
	// kill (no param) default send syscall.SIGTERM
	// kill -2 is syscall.SIGINT
	// kill -9 is syscall.SIGKILL but can't be catch, so don't need add it
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logger.Info("Shutting down server...")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		//nolint
		logger.Fatal("Server forced to shutdown: %v ", err)
	}
	logger.Info("Server exiting\n")
}

func init() {
	logger.New(os.Stdout, true, logger.InfoLevel, map[string]string{})
	//nolint: errcheck
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
		if len(body) == 0 {
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

type bodyLogWriter struct {
	gin.ResponseWriter
	body *bytes.Buffer
}

// Write 用于常见IO
func (w bodyLogWriter) Write(b []byte) (int, error) {
	w.body.Write(b)
	return w.ResponseWriter.Write(b)
}

// returnRessponeMiddleware TODO
// BodyLogMiddleware 记录返回的body
func returnRessponeMiddleware(c *gin.Context) {
	blw := &bodyLogWriter{body: bytes.NewBufferString(""), ResponseWriter: c.Writer}
	c.Writer = blw
	c.Next()
	statusCode := c.Writer.Status()
	// if statusCode >= 400 {
	// ok this is an request with error, let's make a record for it
	// now print body (or log in your preferred way)
	var rp handler.Response
	if blw.body == nil {
		rp = handler.Response{}
		return
	}
	if err := json.Unmarshal(blw.body.Bytes(), &rp); err != nil {
		return
	}
	if lo.IsNotEmpty(rp.RequestID) {
		if err := model.UpdateTbRequestLog(rp.RequestID, map[string]interface{}{
			"response_code": statusCode,
			"update_time":   time.Now()}); err != nil {
			logger.Warn("update request response failed %s", err.Error())
		}
	}
}
