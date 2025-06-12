/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License");
 * you may not use this file except in compliance with the License.
 *
 * You may obtain a copy of the License at
 * https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Package router 定义路由规则
package router

import (
	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"
	"k8s-dbs/common/api"
	"log"

	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

const basePath = "/v4/dbs"

// Router 定义 Router
type Router struct {
	Engine *gin.Engine
}

// Run 启动 HTTP Server
func (r *Router) Run(addr string) {
	if err := r.Engine.Run(addr); err != nil {
		log.Fatalf("Failed to run server: %v", err)
	}
}

// NewRouter 创建并初始化 Router
func NewRouter(db *gorm.DB) *Router {
	router := gin.Default()

	// setup trace
	trace.Setup()
	// apm: add otlgin middleware
	router.Use(otelgin.Middleware("k8s_dbs"))
	// apm: add prom metrics middleware
	metric.NewPrometheus("").Use(router)

	router.GET(basePath+api.HealthCheckURL, api.HealthCheck)

	buildClusterRouter(db, router)

	buildMetaRouter(db, router)

	buildK8sClusterRouter(db, router)

	buildAddonRouter(db, router)

	return &Router{Engine: router}
}
