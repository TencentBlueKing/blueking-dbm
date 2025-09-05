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
	commconst "k8s-dbs/common/constant"
	commutil "k8s-dbs/common/util"
	_ "k8s-dbs/common/validator"
	"k8s-dbs/core"
	_ "k8s-dbs/core/checker/addonoperation"
	"k8s-dbs/core/util"
	metadbaccess "k8s-dbs/metadata/dbaccess"
	metaprovider "k8s-dbs/metadata/provider"
	"k8s-dbs/router"
	_ "k8s-dbs/router/core"
	_ "k8s-dbs/router/dataweb"
	_ "k8s-dbs/router/metadata"
	_ "k8s-dbs/router/terminal"
	routerutil "k8s-dbs/router/util"
	"log"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"k8s.io/client-go/dynamic/dynamicinformer"

	"github.com/gin-gonic/gin"

	dbsinformer "k8s-dbs/informer"
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

	r := router.NewRouter(util.Db.GormDb)

	slog.Info("Finish initial configuration...")

	go startInformer()

	startServer(r.Engine)

}

func startInformer() {
	k8sClusterConfigProvider := metaprovider.
		NewK8sClusterConfigProvider(metadbaccess.NewK8sClusterConfigDbAccess(util.Db.GormDb))
	opsMetaProvider := metaprovider.
		NewK8sCrdOpsRequestProvider(metadbaccess.NewK8sCrdOpsRequestDbAccess(util.Db.GormDb))
	clusterMetaProvider := routerutil.BuildClusterMetaProvider(util.Db.GormDb)

	k8sClusterConfigs, err := k8sClusterConfigProvider.ListConfigsByLimit(commconst.MaxFetchSize)
	if err != nil || len(k8sClusterConfigs) == 0 {
		slog.Error("Failed to find k8s cluster config", "error", err)
		return
	}

	ctx, cancelAll := context.WithCancel(context.Background())
	defer cancelAll() // 确保函数退出时取消所有 Informer
	for _, clusterConfig := range k8sClusterConfigs {
		k8sClient, _ := commutil.NewK8sClient(clusterConfig)
		factory := dynamicinformer.NewDynamicSharedInformerFactory(
			k8sClient.DynamicClient,
			time.Second*30,
		)
		ctxInformer, cancelInformer := context.WithCancel(ctx)
		opsInformer := dbsinformer.NewOpsRequestInformer(clusterConfig, clusterMetaProvider, opsMetaProvider)
		if err := opsInformer.Start(ctxInformer, factory); err != nil {
			cancelInformer()
			slog.Error("failed to start ops informer", "error", err)
			continue
		}
		// 监控是否需要取消（例如通过 channel 信号）
		go func() {
			<-ctx.Done()
			cancelInformer()
		}()
	}
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
