/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package routers routers
package routers

import (
	"net/http"

	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/controller/apply"
	"dbm-services/common/db-resource/internal/controller/manage"
	"dbm-services/common/db-resource/internal/controller/statistic"

	"github.com/gin-gonic/gin"
)

// RegisterRoutes register route
func RegisterRoutes(engine *gin.Engine) {
	apply := apply.ApplyHandler{}
	apply.RegisterRouter(engine)
	// machine resource management
	manage := manage.MachineResourceHandler{}
	manage.RegisterRouter(engine)
	// background router
	background := controller.BackStageHandler{}
	background.RegisterRouter(engine)
	// statistic router
	statistic := statistic.Handler{}
	statistic.RegisterRouter(engine)
	engine.Handle("GET", "/ping", func(context *gin.Context) {
		context.String(http.StatusOK, "pong")
	})
}
