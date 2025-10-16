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

package entity

// MessageType WebSocket消息类型
type MessageType string

const (
	// MessageInit 初始化消息（服务器→客户端）
	MessageInit MessageType = "init"
	// MessageCommand 命令执行（客户端→服务器）
	MessageCommand MessageType = "command"
	// MessageOutput 命令输出（服务器→客户端）
	MessageOutput MessageType = "output"
	// MessageTabComplete Tab补全请求（客户端→服务器）
	MessageTabComplete MessageType = "tab_complete"
	// MessageTabCompleteResult Tab补全结果（服务器→客户端）
	MessageTabCompleteResult MessageType = "tab_complete_result"
	// MessageClear 清空终端
	MessageClear MessageType = "clear"
)

// WebSocketMessage WebSocket消息基础格式
type WebSocketMessage struct {
	Type MessageType `json:"type"`
	ID   string      `json:"id,omitempty"`
	Data interface{} `json:"data"`
}

// InitData 初始化消息数据
type InitData struct {
	User   string `json:"user,omitempty"`
	Host   string `json:"host,omitempty"`
	Prompt string `json:"prompt,omitempty"`
}

// CommandData 命令执行消息数据
type CommandData struct {
	Input string `json:"input"`
}

// OutputData 输出消息数据
type OutputData struct {
	Output string `json:"output"`
	Prompt string `json:"prompt"`
}

// TabCompleteData Tab补全请求数据
type TabCompleteData struct {
	Input string `json:"input"`
}

// TabCompleteResultData Tab补全结果数据
type TabCompleteResultData struct {
	Input       string   `json:"input"`
	Completions []string `json:"completions"`
}
