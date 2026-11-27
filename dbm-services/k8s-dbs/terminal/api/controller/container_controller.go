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

// Package controller 提供已退役的容器终端 HTTP 接口
package controller

import (
	terminalprovider "k8s-dbs/terminal/provider"
	"net/http"

	"github.com/gin-gonic/gin"
)

// ContainerController k8s 容器终端管理 controller
type ContainerController struct {
	TerProvider *terminalprovider.TerminalProvider
}

// OpenTerminal 容器终端接口已退役，统一返回 HTTP 410 Gone。
func (k *ContainerController) OpenTerminal(c *gin.Context) {
	c.AbortWithStatus(http.StatusGone)
}

// NewContainerController 构造函数
func NewContainerController(terminalProvider *terminalprovider.TerminalProvider) *ContainerController {
	return &ContainerController{
		TerProvider: terminalProvider,
	}
}
