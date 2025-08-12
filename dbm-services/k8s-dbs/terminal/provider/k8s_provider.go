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

package provider

import (
	"fmt"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"

	"log"

	corev1 "k8s.io/api/core/v1"
	"k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/tools/remotecommand"

	commutil "k8s-dbs/common/util"

	terminalentity "k8s-dbs/terminal/entity"

	dbserrors "k8s-dbs/errors"

	metaprovider "k8s-dbs/metadata/provider"
)

// TerminalProvider TerminalProvider 结构体
type TerminalProvider struct {
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
}

// OpenTerminal 开启与 Kubernetes Pod 容器的交互式终端
func (k *TerminalProvider) OpenTerminal(
	entity *terminalentity.TerminalEntity,
	conn *websocket.Conn,
	c *gin.Context,
) error {
	// 1. 获取集群配置
	k8sClusterConfig, err := k.clusterConfigProvider.FindConfigByName(entity.K8sClusterName)
	if err != nil {
		writeWSMessage(conn, fmt.Sprintf("[ERROR] 获取集群配置失败: %v", err))
		return dbserrors.NewK8sDbsError(dbserrors.GetMetaDataError, err)
	}

	// 2. 创建 k8s client
	k8sClient, err := commutil.NewK8sClient(k8sClusterConfig)
	if err != nil {
		writeWSMessage(conn, fmt.Sprintf("[ERROR] 创建 k8s client 失败: %v", err))
		return dbserrors.NewK8sDbsError(dbserrors.CreateK8sClientError, err)
	}

	// 3. 构造 exec 请求
	req := k8sClient.ClientSet.CoreV1().RESTClient().Post().
		Resource("pods").
		Name(entity.PodName).
		Namespace(entity.Namespace).
		SubResource("exec")

	// 可以允许 entity 传入自定义 command，默认为 /bin/bash
	command := []string{"sh"}
	/*if len(entity.Command) > 0 {
		command = entity.Command
	}*/

	req.VersionedParams(&corev1.PodExecOptions{
		Command: command,
		Stdin:   true,
		Stdout:  true,
		Stderr:  true,
		TTY:     true, // 可由前端控制是否开启 TTY
	}, scheme.ParameterCodec)

	// 4. 创建 SPDY Executor
	exec, err := remotecommand.NewSPDYExecutor(k8sClient.RestConfig, "POST", req.URL())
	if err != nil {
		writeWSMessage(conn, fmt.Sprintf("[ERROR] 创建 SPDY Executor 失败: %v", err))
		return fmt.Errorf("创建 SPDY Executor 失败: %w", err)
	}

	// 5. 执行交互式流：WebSocket <-> Pod Shell (stdin/stdout/stderr)
	err = exec.StreamWithContext(c.Request.Context(), remotecommand.StreamOptions{
		Stdin:  &wsStdin{conn},
		Stdout: &wsStdout{conn},
		Stderr: &wsStdout{conn},
		Tty:    true,
	})

	if err != nil {
		writeWSMessage(conn, fmt.Sprintf("[ERROR] Stream 执行失败: %v", err))
		return fmt.Errorf("stream 执行失败: %w", err)
	}

	return nil
}

// 辅助函数：向 WebSocket 发送文本消息
func writeWSMessage(conn *websocket.Conn, msg string) {
	if err := conn.WriteMessage(websocket.TextMessage, []byte(msg)); err != nil {
		log.Printf("[WebSocket] 写入消息失败: %v", err)
	}
}

// --- WebSocket --> Pod Stdin (客户端输入发送到容器) ---
// wsStdin 实现了 io.Reader，用于从 WebSocket 读取客户端输入，作为容器的 stdin
type wsStdin struct {
	conn *websocket.Conn
}

// Read 从 WebSocket 读取消息，并将数据拷贝到 p 中，供 remotecommand 使用
func (w *wsStdin) Read(p []byte) (n int, err error) {
	_, data, err := w.conn.ReadMessage()
	fmt.Printf("[STDOUT] 收到客户端输入: %s\n", string(p)) // 调试用
	if err != nil {
		return 0, err
	}

	// 关键点：确保输入以换行符结尾
	if !strings.HasSuffix(string(data), "\n") {
		data = append(data, '\n')
	}
	return copy(p, data), nil
}

// --- Pod Stdout/Stderr --> WebSocket (容器输出发送到客户端) ---
// wsStdout 实现了 io.Writer，用于将容器的 stdout/stderr 写入到 WebSocket 客户端
type wsStdout struct {
	conn *websocket.Conn
}

func (w *wsStdout) Write(p []byte) (n int, err error) {
	fmt.Printf("[STDOUT] 收到容器输出: %s\n", string(p)) // 调试用
	err = w.conn.WriteMessage(websocket.BinaryMessage, p)
	if err != nil {
		return 0, err
	}
	return len(p), nil
}

// NewTerminalProvider 创建 TerminalProvider 实例
func NewTerminalProvider(
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
) *TerminalProvider {
	return &TerminalProvider{
		clusterConfigProvider,
	}
}
