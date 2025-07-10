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

package main

import (
	"context"
	"errors"
	"fmt"
	"k8s-dbs/core"
	"k8s-dbs/core/helper"
	"k8s-dbs/router"
	"log"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
)

// main 函数是程序的入口点，执行以下步骤：
// 1. 初始化系统核心配置
// 2. 创建并配置 Gin 路由引擎
// 3. 启动 HTTP 服务并监听终止信号
// 4. 在接收到终止信号时优雅关闭服务器
func main() {
	slog.Info("Start initial configuration...")

	if err := core.Init(); err != nil {
		log.Fatalf("Failed to initialize core: %v", err)
	}

	r := router.NewRouter(helper.Db.GormDb)

	slog.Info("Finish initial configuration...")

	startServer(r.Engine)
}

// startServer 启动 HTTP 服务并处理优雅关闭
func startServer(r *gin.Engine) {
	server := &http.Server{
		Addr:    ":8000",
		Handler: r,
	}

	go func() {
		slog.Info("Start server...")
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			slog.Error("Failed to start server", "error", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	slog.Info("Shutdown Server ...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := server.Shutdown(ctx); err != nil {
		slog.Error("Server forced to shutdown", "error", err)
		panic(fmt.Errorf("fatal error: %w", err)) // 触发 panic
	}

	slog.Info("Server exited properly")
}
