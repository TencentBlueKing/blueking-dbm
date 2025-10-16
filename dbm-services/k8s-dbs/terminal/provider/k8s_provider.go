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
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"

	commutil "k8s-dbs/common/util"
	dbserrors "k8s-dbs/errors"
	metaprovider "k8s-dbs/metadata/provider"
	terminalentity "k8s-dbs/terminal/entity"
	terminalutil "k8s-dbs/terminal/util"
)

// TerminalProvider TerminalProvider 结构体
type TerminalProvider struct {
	clusterConfigProvider metaprovider.K8sClusterConfigProvider
}

// OpenTerminal 开启与 Kubernetes Pod 容器的交互式终端
func (k *TerminalProvider) OpenTerminal(
	entity *terminalentity.TerminalEntity,
	conn *websocket.Conn,
	_ *gin.Context,
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

	// 3. 创建持久 shell
	shell, err := terminalutil.NewShell(k8sClient, entity.Namespace, entity.PodName)
	if err != nil {
		writeWSMessage(conn, fmt.Sprintf("[ERROR] 创建持久 shell 失败: %v", err))
		return dbserrors.NewK8sDbsError(dbserrors.CreateK8sClientError, err)
	}
	defer shell.Close()

	// 4. 初始化：获取用户名和初始 cwd
	userResult := shell.Execute("whoami")
	userName := "root"
	if userResult.Error == nil {
		userName = strings.TrimSpace(userResult.Output)
	}

	session := terminalutil.NewTerminalSession(entity.PodName, userName)
	session.SetCwd(shell.GetCwd())

	// 5. 发送初始化消息
	initMsg := terminalentity.WebSocketMessage{
		Type: terminalentity.MessageInit,
		Data: terminalentity.InitData{User: userName, Host: entity.PodName, Prompt: session.BuildPrompt()},
	}
	_ = conn.WriteJSON(initMsg)

	// 6. 循环处理 WebSocket 消息
	for {
		var msg terminalentity.WebSocketMessage
		err := conn.ReadJSON(&msg)
		if err != nil {
			slog.Error("读取消息失败", "error", err)
			continue
		}

		switch msg.Type {
		case terminalentity.MessageCommand:
			var cd terminalentity.CommandData
			_ = decodeData(msg.Data, &cd)
			k.handleCommand(conn, shell, session, cd.Input)

		case terminalentity.MessageTabComplete:
			var td terminalentity.TabCompleteData
			_ = decodeData(msg.Data, &td)
			k.handleTabComplete(conn, shell, msg.ID, td.Input)
		}
	}
}

// completeCommand 将输入和补全结果合并成完整命令
func completeCommand(input string, completion string) string {
	input = strings.TrimRight(input, " \t")
	if input == "" {
		return completion
	}

	// 找到最后一个 token 的起始位置
	idx := strings.LastIndexAny(input, " \t")
	if idx == -1 {
		// 整个输入就是一个 token，直接替换
		return completion
	}

	// 替换最后一个 token
	return input[:idx+1] + completion
}

// handleCommand 处理命令执行
func (k *TerminalProvider) handleCommand(
	conn *websocket.Conn,
	shell *terminalutil.Shell,
	session *terminalutil.TerminalSession,
	input string,
) {
	input = strings.TrimSpace(input)
	if input == "" {
		return
	}

	// 如果是纯 clear 命令，直接返回 clear 消息，不执行
	if input == "clear" {
		resp := terminalentity.WebSocketMessage{
			Type: terminalentity.MessageClear,
			Data: terminalentity.OutputData{Output: "", Prompt: session.BuildPrompt()},
		}
		_ = conn.WriteJSON(resp)
		return
	}

	// 在持久 shell 中执行命令
	result := shell.Execute(input)

	if result.Error != nil {
		slog.Error("执行命令失败", "error", result.Error, "input", input)
		// 返回错误信息
		resp := terminalentity.WebSocketMessage{
			Type: terminalentity.MessageOutput,
			Data: terminalentity.OutputData{
				Output: fmt.Sprintf("错误: %v\n", result.Error),
				Prompt: session.BuildPrompt(),
			},
		}
		_ = conn.WriteJSON(resp)
		return
	}

	// 更新 cwd
	if result.Cwd != "" {
		session.SetCwd(result.Cwd)
	}

	// 返回输出
	resp := terminalentity.WebSocketMessage{
		Type: terminalentity.MessageOutput,
		Data: terminalentity.OutputData{Output: result.Output, Prompt: session.BuildPrompt()},
	}
	_ = conn.WriteJSON(resp)
}

// handleTabComplete 处理 Tab 补全
func (k *TerminalProvider) handleTabComplete(
	conn *websocket.Conn,
	shell *terminalutil.Shell,
	msgID string,
	input string,
) {
	// 在持久 shell 中执行补全
	results := shell.Complete(input)

	// 当只有一个补全结果时，将补全结果替换为完整命令
	completions := results
	if len(results) == 1 {
		fullCommand := completeCommand(input, results[0])
		completions = []string{fullCommand}
	}

	resp := terminalentity.WebSocketMessage{
		Type: terminalentity.MessageTabCompleteResult,
		ID:   msgID,
		Data: terminalentity.TabCompleteResultData{Input: input, Completions: completions},
	}
	_ = conn.WriteJSON(resp)
}

// writeWSMessage 向 WebSocket 发送文本消息
func writeWSMessage(conn *websocket.Conn, msg string) {
	if err := conn.WriteMessage(websocket.TextMessage, []byte(msg)); err != nil {
		slog.Error("写入消息失败", "error", err)
	}
}

// decodeData 解码数据
func decodeData(src interface{}, dst interface{}) error {
	b, err := json.Marshal(src)
	if err != nil {
		return err
	}
	return json.Unmarshal(b, dst)
}

// NewTerminalProvider 创建 TerminalProvider 实例
func NewTerminalProvider(
	clusterConfigProvider metaprovider.K8sClusterConfigProvider,
) *TerminalProvider {
	return &TerminalProvider{
		clusterConfigProvider,
	}
}
