/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package main TODO
/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
// Package main main
package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"dbm-services/mysql/db-simulation/app/config"

	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"

	"dbm-services/common/db-resource/internal/middleware"
	"dbm-services/common/db-resource/internal/routers"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-contrib/pprof"
	"github.com/gin-contrib/requestid"
	"github.com/gin-gonic/gin"
	"github.com/robfig/cron/v3"
)

var buildstamp = ""
var githash = ""
var version = ""

func main() {
	logger.Info("buildstamp:%s,githash:%s,version:%s", buildstamp, githash, version)

	app := gin.New()
	pprof.Register(app)

	// setup trace
	trace.Setup()
	// apm: add otlgin middleware
	app.Use(
		gin.Recovery(),
		otelgin.Middleware("db_resource"),
	)
	// apm: add prom metrics middleware
	metric.NewPrometheus("").Use(app)

	app.Use(requestid.New())
	app.Use(middleware.ApiLogger)
	app.Use(middleware.BodyLogMiddleware)
	routers.RegisterRoutes(app)
	app.POST("/app", func(ctx *gin.Context) {
		ctx.SecureJSON(http.StatusOK, map[string]interface{}{"buildstamp": buildstamp, "githash": githash,
			"version": version})
	})
	lcron := cron.New()
	registerCrontab(lcron)
	lcron.Start()
	defer lcron.Stop()

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

// init init logger
func init() {
	if err := initLogger(); err != nil {
		logger.Fatal("Init Logger Failed %s", err.Error())
		return
	}
}

// LocalCron define local crontab
type LocalCron struct {
	Name string
	Spec string
	Func func()
}

func registerCrontab(localcron *cron.Cron) {
	localCrontabs := []LocalCron{
		{
			Name: "定时更新gse状态",
			Spec: "@every 1h",
			Func: func() {
				if err := task.UpdateResourceGseAgentStatus(); err != nil {
					logger.Error("update gse status %s", err.Error())
				}
			},
		},
		{
			Name: "扫描检查主机是否被手动拿去用了",
			Spec: "@every 1h",
			Func: func() {
				if err := task.InspectCheckResource(); err != nil {
					logger.Error("inspect check resource %s", err.Error())
				}
			},
		},
		{
			Name: "同步主机硬件信息",
			Spec: "@every 12h",
			Func: func() {
				if err := task.AsyncResourceHardInfo(); err != nil {
					logger.Error("async machine hardinfo failed:%s", err.Error())
				}
			},
		},
	}
	for _, cron := range localCrontabs {
		if _, err := localcron.AddFunc(cron.Spec, cron.Func); err != nil {
			logger.Error("add %s crontab failed %v", cron.Name, err)
		}
	}
}

// initLogger initialization log
func initLogger() (err error) {
	var writer *os.File
	formatJson := true
	level := logger.InfoLevel
	writer = os.Stdout
	l := logger.New(writer, formatJson, level, map[string]string{})
	logger.ResetDefault(l)
	defer func() {
		if errx := l.Sync(); errx != nil {
			logger.Warn("sync log failed %v", errx)
		}
	}()
	return
}
