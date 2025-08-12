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

package controller

import (
	"k8s-dbs/common/api"
	commutil "k8s-dbs/common/util"
	"k8s-dbs/errors"
	terminalentity "k8s-dbs/terminal/entity"
	terminalprovider "k8s-dbs/terminal/provider"
	terminalreq "k8s-dbs/terminal/vo/request"
	"log/slog"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

// WebSocket升级器
var upgrader = websocket.Upgrader{
	CheckOrigin: func(_ *http.Request) bool {
		// ⚠️ 生产环境一定要限制来源，比如允许的域名/IP
		return true
	},
}

// ContainerController k8s 容器终端管理 controller
type ContainerController struct {
	TerProvider *terminalprovider.TerminalProvider
}

// OpenTerminal 开启与 Pod 容器的交互式终端
func (k *ContainerController) OpenTerminal(c *gin.Context) {
	// 1. 参数绑定与校验
	var req terminalreq.TerminalRequest
	if err := commutil.DecodeParams(c, commutil.BuildParams, &req, nil); err != nil {
		api.ErrorResponse(c, errors.NewK8sDbsError(errors.ServerError, err))
		return
	}
	slog.Info("OpenTerminal")
	slog.Info("go req ", "req", req)
	// ⚠️ 基础必填参数校验（建议根据实际业务补充）
	if req.K8sClusterName == "" || req.Namespace == "" || req.PodName == "" || req.ClusterName == "" {
		api.ErrorResponse(c, errors.NewK8sDbsError(errors.ParameterInvalidError, nil))
		return
	}

	// 2. 升级为 WebSocket（注意：升级之后，HTTP 响应通道已切换，不能再返回 JSON）
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		slog.Error("upgrade error", "error", err)
		// 注意：此处不能返回 HTTP 响应，因为连接已经升级
		return
	}
	defer conn.Close()

	// 3. 构造领域对象 TerminalEntity
	entity := &terminalentity.TerminalEntity{
		K8sClusterName: req.K8sClusterName,
		ClusterName:    req.ClusterName,
		Namespace:      req.Namespace,
		PodName:        req.PodName,
	}

	// 4. 调用 Provider 打开终端交互
	err = k.TerProvider.OpenTerminal(entity, conn, c)
	if err != nil {
		slog.Error("OpenTerminal failed", "err", err)
		// ⚠️ 注意：WebSocket 已建立，这里无法通过 HTTP 返回错误给客户端
		// 但 Provider 内部应该通过 conn.WriteMessage() 发送错误信息给前端
		return
	}
}

// NewContainerController 构造函数
func NewContainerController(terminalProvider *terminalprovider.TerminalProvider) *ContainerController {
	return &ContainerController{
		TerProvider: terminalProvider,
	}
}
