/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package router TODO
package router

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/service"
	"dbm-services/mysql/db-simulation/handler"

	"github.com/gin-gonic/gin"
)

// RegisterRouter reg routers
func RegisterRouter(engine *gin.Engine) {
	engine.POST("/app/debug", TurnOnDebug)
	// mysql
	g := engine.Group("/mysql")
	g.POST("/simulation", handler.Dbsimulation)
	g.POST("/task", handler.QueryTask)
	// syntax
	s := engine.Group("/syntax")
	s.POST("/check/file", handler.SyntaxCheckFile)
	s.POST("/check/sql", handler.SyntaxCheckSQL)
	s.POST("/upload/ddl/tbls", handler.CreateAndUploadDDLTblListFile)
	// rule
	r := engine.Group("/rule")
	r.POST("/manage", handler.ManageRule)
	r.GET("/getall", handler.GetAllRule)
	r.POST("/update", handler.UpdateRule)
	// spider
	sp := engine.Group("/spider")
	sp.POST("/simulation", handler.SpiderClusterSimulation)
	sp.POST("/create", handler.CreateTmpSpiderPodCluster)
}

// TurnOnDebug TODO
func TurnOnDebug(r *gin.Context) {
	logger.Info("current delpod: %v", service.DelPod)
	service.DelPod = !service.DelPod
	r.JSON(0, map[string]interface{}{
		"delpod": service.DelPod,
	})
}
