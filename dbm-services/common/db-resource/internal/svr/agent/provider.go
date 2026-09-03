/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package agent 提供 LLM 智能体功能，用于分析资源匹配失败的原因
package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
)

// LLMProvider LLM 提供商抽象接口
type LLMProvider interface {
	// Chat 发送聊天请求
	Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error)
	// Name 返回提供商名称
	Name() string
}

// ChatRequest 聊天请求
type ChatRequest struct {
	Messages []Message        `json:"messages"`
	Tools    []ToolDefinition `json:"tools,omitempty"`
	// ToolChoice 控制本轮能否发起工具调用，"none" 表示必须用文本作答。
	// 注意要保留 Tools 声明再配合 "none"：直接摘掉 Tools 会让部分模型
	// （如 deepseek）把内部工具调用标记原样吐成纯文本，而不是给出结论
	ToolChoice any `json:"tool_choice,omitempty"`
}

// Message 消息结构
type Message struct {
	Role       string     `json:"role"`                   // system/user/assistant/tool
	Content    string     `json:"content"`                // 消息内容
	ToolCalls  []ToolCall `json:"tool_calls,omitempty"`   // assistant 调用的工具
	ToolCallID string     `json:"tool_call_id,omitempty"` // tool 响应时的 ID
	Name       string     `json:"name,omitempty"`         // tool 名称
}

// ToolCall 工具调用
type ToolCall struct {
	ID       string       `json:"id"`
	Type     string       `json:"type"` // function
	Function FunctionCall `json:"function"`
}

// FunctionCall 函数调用
type FunctionCall struct {
	Name      string `json:"name"`
	Arguments string `json:"arguments"` // JSON 格式的参数
}

// ToolDefinition 工具定义
type ToolDefinition struct {
	Type     string             `json:"type"` // function
	Function FunctionDefinition `json:"function"`
}

// FunctionDefinition 函数定义
type FunctionDefinition struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Parameters  map[string]interface{} `json:"parameters"`
}

// ToolChoiceNone 禁止本轮发起工具调用，要求以文本作答
const ToolChoiceNone = "none"

// toolCallMarkupMarkers 模型未能发起结构化工具调用时，会把内部特殊标记原样吐成文本，
// 例如 deepseek 的 <｜DSML｜tool_calls>。这类内容不是分析结论，必须识别出来丢弃
var toolCallMarkupMarkers = []string{"DSML", "<｜", "<|tool_calls", "tool▁calls"}

// LooksLikeToolCallMarkup 判断内容是否是泄漏出来的工具调用标记而非正常回答
func LooksLikeToolCallMarkup(content string) bool {
	for _, marker := range toolCallMarkupMarkers {
		if strings.Contains(content, marker) {
			return true
		}
	}
	return false
}

// ChatResponse 聊天响应
type ChatResponse struct {
	Content      string     `json:"content"`              // 文本响应内容
	ToolCalls    []ToolCall `json:"tool_calls,omitempty"` // 工具调用请求
	FinishReason string     `json:"finish_reason"`        // stop/tool_calls
}

// HasToolCalls 检查是否有工具调用
func (r *ChatResponse) HasToolCalls() bool {
	return len(r.ToolCalls) > 0
}

// NewSystemMessage 创建系统消息
func NewSystemMessage(content string) Message {
	return Message{
		Role:    "system",
		Content: content,
	}
}

// NewUserMessage 创建用户消息
func NewUserMessage(content string) Message {
	return Message{
		Role:    "user",
		Content: content,
	}
}

// NewAssistantMessage 创建助手消息
func NewAssistantMessage(content string) Message {
	return Message{
		Role:    "assistant",
		Content: content,
	}
}

// NewAssistantToolCallMessage 创建带工具调用的助手消息
func NewAssistantToolCallMessage(toolCalls []ToolCall) Message {
	return Message{
		Role:      "assistant",
		ToolCalls: toolCalls,
	}
}

// NewToolResultMessage 创建工具结果消息
func NewToolResultMessage(toolCallID, name string, result interface{}) Message {
	content, _ := json.Marshal(result)
	return Message{
		Role:       "tool",
		Content:    string(content),
		ToolCallID: toolCallID,
		Name:       name,
	}
}

// NewFunctionTool 创建函数工具定义
func NewFunctionTool(name, description string, parameters map[string]interface{}) ToolDefinition {
	return ToolDefinition{
		Type: "function",
		Function: FunctionDefinition{
			Name:        name,
			Description: description,
			Parameters:  parameters,
		},
	}
}

// ProviderError 提供商错误
type ProviderError struct {
	Provider string
	Message  string
	Err      error
}

func (e *ProviderError) Error() string {
	if e.Err != nil {
		return fmt.Sprintf("[%s] %s: %v", e.Provider, e.Message, e.Err)
	}
	return fmt.Sprintf("[%s] %s", e.Provider, e.Message)
}

func (e *ProviderError) Unwrap() error {
	return e.Err
}
