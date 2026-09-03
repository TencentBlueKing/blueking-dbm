/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package agent

import (
	"context"
	"errors"
	"strings"
	"testing"
)

// stagedConclusion 模拟 Agent 中途给出的阶段性结论，用于验证兜底捞取
const stagedConclusion = "阶段性结论"

// fakeProvider 记录收到的请求，返回预设响应
type fakeProvider struct {
	lastRequest *ChatRequest
	callCount   int
	response    *ChatResponse
	err         error
}

func (f *fakeProvider) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	f.callCount++
	f.lastRequest = req
	if f.err != nil {
		return nil, f.err
	}
	return f.response, nil
}

func (f *fakeProvider) Name() string { return "fake" }

// toolCallConversation 模拟耗尽迭代预算后的消息序列：末尾是工具返回，不是 assistant
func toolCallConversation() []Message {
	return []Message{
		NewSystemMessage("system"),
		NewUserMessage("分析资源不足原因"),
		NewAssistantToolCallMessage([]ToolCall{{ID: "call_1", Type: "function",
			Function: FunctionCall{Name: "query_pool_stats", Arguments: "{}"}}}),
		NewToolResultMessage("call_1", "query_pool_stats", map[string]int{"count": 0}),
	}
}

// TestResolveTemperature 未配置取默认值，显式配 0 必须保留
func TestResolveTemperature(t *testing.T) {
	if got := resolveTemperature(nil); got != DefaultAnalysisTemperature {
		t.Errorf("未配置时期望默认 %.2f, 实际 %.2f", DefaultAnalysisTemperature, got)
	}

	zero := float32(0)
	if got := resolveTemperature(&zero); got != 0 {
		t.Errorf("显式配置 0 应保留 0, 实际 %.2f, 用指针就是为了区分「未配置」和「配 0」", got)
	}

	low := float32(0.2)
	if got := resolveTemperature(&low); got != 0.2 {
		t.Errorf("期望 0.2, 实际 %.2f", got)
	}
}

// TestSalvageSkipsToolMessage 兜底必须往回找 assistant，不能只看末尾那条工具返回
func TestSalvageSkipsToolMessage(t *testing.T) {
	messages := toolCallConversation()
	messages = append(messages, NewAssistantMessage("这是中途给出的阶段性结论"))
	messages = append(messages, NewAssistantToolCallMessage([]ToolCall{{ID: "call_2"}}))
	messages = append(messages, NewToolResultMessage("call_2", "execute_custom_sql", []string{}))

	result := &ExecutionResult{}
	salvageLastAssistantMessage(messages, result)

	if result.FinalResponse != "这是中途给出的阶段性结论" {
		t.Errorf("应捞回最后一条有内容的 assistant 消息, 实际: %q", result.FinalResponse)
	}
}

// TestSalvageNothingToRecover 全程没有 assistant 文本内容时保持为空
func TestSalvageNothingToRecover(t *testing.T) {
	result := &ExecutionResult{}
	salvageLastAssistantMessage(toolCallConversation(), result)

	if result.FinalResponse != "" {
		t.Errorf("没有可捞的内容时应保持为空, 实际: %q", result.FinalResponse)
	}
}

// fakeToolDefs 收口请求需要携带的工具声明
func fakeToolDefs() []ToolDefinition {
	return []ToolDefinition{
		NewFunctionTool("query_pool_stats", "查询资源池统计", map[string]interface{}{}),
		NewFunctionTool("verify_prediction", "验证推断", map[string]interface{}{}),
	}
}

// TestFinalizeForcesConclusion 预算耗尽后应再问一次并拿到结论
func TestFinalizeForcesConclusion(t *testing.T) {
	provider := &fakeProvider{response: &ChatResponse{
		Content:      "最终结论：跨园区强制打散摆不开",
		FinishReason: "stop",
	}}
	executor := &AgentExecutor{provider: provider}
	messages := toolCallConversation()
	result := &ExecutionResult{}

	executor.finalizeWithoutToolUse(context.Background(), messages, fakeToolDefs(), result)

	if !result.Success {
		t.Error("拿到结论后应标记成功")
	}
	if result.FinalResponse != "最终结论：跨园区强制打散摆不开" {
		t.Errorf("最终结论不符, 实际: %q", result.FinalResponse)
	}
	if provider.callCount != 1 {
		t.Errorf("应只补一次调用, 实际 %d 次", provider.callCount)
	}

	// 关键：必须保留工具声明再用 tool_choice=none 禁用，
	// 直接摘掉 Tools 会让 deepseek 把 DSML 标记吐成文本
	if len(provider.lastRequest.Tools) != 2 {
		t.Errorf("收口请求必须保留工具声明, 实际带了 %d 个", len(provider.lastRequest.Tools))
	}
	if provider.lastRequest.ToolChoice != ToolChoiceNone {
		t.Errorf("收口请求应设置 tool_choice=none, 实际: %v", provider.lastRequest.ToolChoice)
	}

	last := provider.lastRequest.Messages[len(provider.lastRequest.Messages)-1]
	if last.Role != "user" || !strings.Contains(last.Content, "不能再调用任何工具") {
		t.Errorf("应在末尾追加收口指令, 实际: role=%s content=%q", last.Role, last.Content)
	}
	if len(provider.lastRequest.Messages) != len(messages)+1 {
		t.Errorf("收口请求应保留全部历史再加一条, 期望 %d 条, 实际 %d 条",
			len(messages)+1, len(provider.lastRequest.Messages))
	}
}

// TestFinalizeRejectsToolCallMarkup 收口拿到的若是 DSML 工具调用标记，不能当结论
func TestFinalizeRejectsToolCallMarkup(t *testing.T) {
	// 线上实际观测到的返回：模型想再调 verify_prediction，标记原样漏成文本
	markup := "\n\n<｜DSML｜tool_calls>\n<｜DSML｜invoke name=\"verify_prediction\">\n" +
		"<｜DSML｜parameter name=\"city\" string=\"true\"\u003e香港</｜DSML｜parameter>\n" +
		"</｜DSML｜invoke>\n</｜DSML｜tool_calls>"
	provider := &fakeProvider{response: &ChatResponse{Content: markup, FinishReason: "stop"}}
	executor := &AgentExecutor{provider: provider}
	messages := append(toolCallConversation(), NewAssistantMessage(stagedConclusion))
	result := &ExecutionResult{}

	executor.finalizeWithoutToolUse(context.Background(), messages, fakeToolDefs(), result)

	if result.Success {
		t.Error("工具调用标记不是结论, 不应标记成功")
	}
	if result.FinalResponse == markup {
		t.Error("不应把工具调用标记当成最终结论")
	}
	if result.FinalResponse != stagedConclusion {
		t.Errorf("应退回兜底捞取, 实际: %q", result.FinalResponse)
	}
}

// TestFinalizeProviderError 收口调用失败时退回兜底捞取
func TestFinalizeProviderError(t *testing.T) {
	provider := &fakeProvider{err: errors.New("gateway 500")}
	executor := &AgentExecutor{provider: provider}
	messages := append(toolCallConversation(), NewAssistantMessage(stagedConclusion))
	result := &ExecutionResult{}

	executor.finalizeWithoutToolUse(context.Background(), messages, fakeToolDefs(), result)

	if result.Success {
		t.Error("收口失败不应标记成功")
	}
	if result.FinalResponse != stagedConclusion {
		t.Errorf("应退回兜底捞取, 实际: %q", result.FinalResponse)
	}
}

// TestFinalizeEmptyContent 收口返回空内容同样不算成功
func TestFinalizeEmptyContent(t *testing.T) {
	provider := &fakeProvider{response: &ChatResponse{Content: "", FinishReason: "length"}}
	executor := &AgentExecutor{provider: provider}
	result := &ExecutionResult{}

	executor.finalizeWithoutToolUse(context.Background(), toolCallConversation(),
		fakeToolDefs(), result)

	if result.Success {
		t.Error("空内容不应标记成功")
	}
	if result.FinalResponse != "" {
		t.Errorf("空内容时最终响应应为空, 实际: %q", result.FinalResponse)
	}
}

// TestFinalizeContextDone 上下文已结束时不再浪费一次调用
func TestFinalizeContextDone(t *testing.T) {
	provider := &fakeProvider{response: &ChatResponse{Content: "不该被调用"}}
	executor := &AgentExecutor{provider: provider}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	result := &ExecutionResult{}

	executor.finalizeWithoutToolUse(ctx, append(toolCallConversation(),
		NewAssistantMessage(stagedConclusion)), fakeToolDefs(), result)

	if provider.callCount != 0 {
		t.Errorf("上下文已结束不应再请求, 实际调用 %d 次", provider.callCount)
	}
	if result.FinalResponse != stagedConclusion {
		t.Errorf("应退回兜底捞取, 实际: %q", result.FinalResponse)
	}
}

// TestLooksLikeToolCallMarkup 识别泄漏的工具调用标记，同时不误伤正常中文结论
func TestLooksLikeToolCallMarkup(t *testing.T) {
	markups := []string{
		"<｜DSML｜tool_calls><｜DSML｜invoke name=\"verify_prediction\">",
		"\n\n<｜DSML｜parameter name=\"city\" string=\"true\">香港</｜DSML｜parameter>",
		"<|tool_calls|>",
	}
	for _, m := range markups {
		if !LooksLikeToolCallMarkup(m) {
			t.Errorf("应识别为工具调用标记: %q", m)
		}
	}

	normals := []string{
		"香港园区可用资源不足，跨园区强制打散无法满足 3 台的分布要求。",
		"建议放宽亲和性到 NONE，或补充 SSD 机型资源。",
		"",
	}
	for _, n := range normals {
		if LooksLikeToolCallMarkup(n) {
			t.Errorf("正常结论不应被误判为标记: %q", n)
		}
	}
}

// TestCheckExecutionProducedRejectsMarkup 标记泄漏必须落库为失败，而不是空报告
func TestCheckExecutionProducedRejectsMarkup(t *testing.T) {
	err := checkExecutionProduced(&ExecutionResult{
		FinalResponse: "<｜DSML｜tool_calls><｜DSML｜invoke name=\"verify_prediction\">",
		Iterations:    15,
	})
	if err == nil {
		t.Fatal("工具调用标记必须报错")
	}
	if !strings.Contains(err.Error(), "tool-call markup") {
		t.Errorf("错误信息应说明是工具调用标记, 实际: %v", err)
	}
}

// TestCheckExecutionProduced 没有产出必须报错，且带上真实原因
func TestCheckExecutionProduced(t *testing.T) {
	if err := checkExecutionProduced(&ExecutionResult{FinalResponse: "有结论"}); err != nil {
		t.Errorf("有产出时不应报错, 实际: %v", err)
	}

	// 迭代耗尽的原因必须透出来，否则排查时只能看到一份空报告
	err := checkExecutionProduced(&ExecutionResult{
		Error:      "max iterations (15) reached",
		Iterations: 15,
	})
	if err == nil {
		t.Fatal("没有产出时必须报错")
	}
	if !strings.Contains(err.Error(), "max iterations (15) reached") {
		t.Errorf("错误里应带上迭代耗尽的原因, 实际: %v", err)
	}

	err = checkExecutionProduced(&ExecutionResult{})
	if err == nil || !strings.Contains(err.Error(), "empty response from LLM") {
		t.Errorf("没有原因时应给出默认说明, 实际: %v", err)
	}
}
