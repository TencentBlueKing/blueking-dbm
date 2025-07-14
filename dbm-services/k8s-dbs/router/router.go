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

	baseRouter := router.Group(basePath)
	buildHealthRouter(baseRouter)
	buildAPIRouters(db, baseRouter)

	return &Router{Engine: router}
}

func buildHealthRouter(router *gin.RouterGroup) gin.IRoutes {
	return router.GET(api.HealthCheckURL, api.HealthCheck)
}

// CustomRouterBuilder 自定义 Router 构建函数
type CustomRouterBuilder func(db *gorm.DB, engine *gin.RouterGroup)

var CustomRouterBuilders []CustomRouterBuilder

// RegisterAPIRouterBuilder 注册 CustomRouterBuilder
func RegisterAPIRouterBuilder(builder CustomRouterBuilder) {
	CustomRouterBuilders = append(CustomRouterBuilders, builder)
}

// buildAPIRouters 元数据路由构建
func buildAPIRouters(db *gorm.DB, engine *gin.RouterGroup) {
	for _, builder := range CustomRouterBuilders {
		builder(db, engine)
	}
}
