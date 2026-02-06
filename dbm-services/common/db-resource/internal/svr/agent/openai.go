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
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"dbm-services/common/db-resource/internal/config"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/sashabaranov/go-openai"
)

// OpenAIProvider OpenAI 提供商实现
type OpenAIProvider struct {
	client      *openai.Client
	model       string
	maxTokens   int
	temperature float32
}

// OpenAIConfig OpenAI 配置
type OpenAIConfig struct {
	APIKey      string  `yaml:"api_key" mapstructure:"api_key"`
	BaseURL     string  `yaml:"base_url" mapstructure:"base_url"`
	Model       string  `yaml:"model" mapstructure:"model"`
	MaxTokens   int     `yaml:"max_tokens" mapstructure:"max_tokens"`
	Temperature float32 `yaml:"temperature" mapstructure:"temperature"`
}

// NewBkAiDevProvider 创建蓝鲸 AI 开发平台提供商
func NewBkAiDevProvider(appCode, appSecret string) *OpenAIProvider {
	// 构建网关校验头
	authHeader := map[string]string{
		"bk_app_code":   appCode,
		"bk_app_secret": appSecret,
	}
	authHeaderJSON, _ := json.Marshal(authHeader)

	// #region agent log - 假设 A: 记录 HTTP Client 超时配置
	// 使用较长的超时时间以支持 LLM 思考型模型（dsv32-thinking 等）
	// 这些模型可能需要数分钟才能返回结果
	httpTimeout := LLMHTTPClientTimeout
	logger.Info("[DEBUG-A] Creating BkAiDevProvider - httpTimeout: %.2fs, baseURL: %s",
		httpTimeout.Seconds(), config.AppConfig.LLM.BkAi.BaseURL)
	// #endregion

	// 创建配置
	aiConfig := openai.DefaultConfig("empty")
	aiConfig.BaseURL = config.AppConfig.LLM.BkAi.BaseURL
	// 设置自定义 HTTP 客户端以添加 headers
	aiConfig.HTTPClient = &http.Client{
		Timeout: httpTimeout,
		Transport: &customTransport{
			headers: map[string]string{
				"X-Bkapi-Authorization": string(authHeaderJSON),
			},
		},
	}
	client := openai.NewClientWithConfig(aiConfig)

	// 设置默认值
	model := config.AppConfig.LLM.BkAi.Model
	if model == "" {
		model = "deepseek-r1"
	}
	maxTokens := config.AppConfig.LLM.BkAi.MaxTokens
	if maxTokens == 0 {
		maxTokens = 4096
	}
	temperature := float32(0.7)

	return &OpenAIProvider{
		client:      client,
		model:       model,
		maxTokens:   maxTokens,
		temperature: temperature,
	}
}

// customTransport 自定义传输层，用于添加请求头
type customTransport struct {
	headers map[string]string
	base    http.RoundTripper
}

func (t *customTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	// 使用默认传输层
	if t.base == nil {
		t.base = http.DefaultTransport
	}

	// 添加自定义 headers
	for k, v := range t.headers {
		req.Header.Set(k, v)
	}

	return t.base.RoundTrip(req)
}

// NewOpenAIProvider 创建 OpenAI 提供商
func NewOpenAIProvider(cfg OpenAIConfig) *OpenAIProvider {
	config := openai.DefaultConfig(cfg.APIKey)
	if cfg.BaseURL != "" {
		config.BaseURL = cfg.BaseURL
	}

	client := openai.NewClientWithConfig(config)

	model := cfg.Model
	if model == "" {
		model = "gpt-4o"
	}

	maxTokens := cfg.MaxTokens
	if maxTokens == 0 {
		maxTokens = 4096
	}

	temperature := cfg.Temperature
	if temperature == 0 {
		temperature = 0.3
	}

	return &OpenAIProvider{
		client:      client,
		model:       model,
		maxTokens:   maxTokens,
		temperature: temperature,
	}
}

// Name 返回提供商名称
func (p *OpenAIProvider) Name() string {
	return "openai"
}

// Chat 发送聊天请求
func (p *OpenAIProvider) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	// #region agent log - 假设 A/B/F/G: 记录请求开始时间和 context deadline
	startTime := time.Now()
	deadline, hasDeadline := ctx.Deadline()
	timeoutDuration := time.Duration(0)
	if hasDeadline {
		timeoutDuration = time.Until(deadline)
	}
	// 检查 context 是否已经被取消
	ctxErr := ctx.Err()
	logger.Info("[DEBUG-A/B/F/G] Chat request started - model: %s, messages: %d, tools: %d, hasDeadline: %v, timeoutDuration: %.2fs, ctxErr: %v",
		p.model, len(req.Messages), len(req.Tools), hasDeadline, timeoutDuration.Seconds(), ctxErr)
	// #endregion

	// 转换消息格式
	messages := make([]openai.ChatCompletionMessage, 0, len(req.Messages))
	for _, msg := range req.Messages {
		chatMsg := openai.ChatCompletionMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}

		// 处理工具调用
		if len(msg.ToolCalls) > 0 {
			toolCalls := make([]openai.ToolCall, 0, len(msg.ToolCalls))
			for _, tc := range msg.ToolCalls {
				toolCalls = append(toolCalls, openai.ToolCall{
					ID:   tc.ID,
					Type: openai.ToolType(tc.Type),
					Function: openai.FunctionCall{
						Name:      tc.Function.Name,
						Arguments: tc.Function.Arguments,
					},
				})
			}
			chatMsg.ToolCalls = toolCalls
		}

		// 处理工具响应
		if msg.ToolCallID != "" {
			chatMsg.ToolCallID = msg.ToolCallID
			chatMsg.Name = msg.Name
		}

		messages = append(messages, chatMsg)
	}

	// 转换工具定义
	var tools []openai.Tool
	if len(req.Tools) > 0 {
		tools = make([]openai.Tool, 0, len(req.Tools))
		for _, tool := range req.Tools {
			tools = append(tools, openai.Tool{
				Type: openai.ToolTypeFunction,
				Function: &openai.FunctionDefinition{
					Name:        tool.Function.Name,
					Description: tool.Function.Description,
					Parameters:  tool.Function.Parameters,
				},
			})
		}
	}

	// 构建请求
	chatReq := openai.ChatCompletionRequest{
		Model:       p.model,
		Messages:    messages,
		MaxTokens:   p.maxTokens,
		Temperature: p.temperature,
		TopP:        0.9,
	}

	if len(tools) > 0 {
		chatReq.Tools = tools
	}

	// #region agent log - 假设 C/D: 记录请求发送时间点
	beforeAPICall := time.Now()
	logger.Info("[DEBUG-C/D] Calling LLM API - elapsed: %.2fs, model: %s, maxTokens: %d",
		beforeAPICall.Sub(startTime).Seconds(), p.model, p.maxTokens)
	// #endregion

	// 发送请求
	resp, err := p.client.CreateChatCompletion(ctx, chatReq)

	// #region agent log - 假设 A/B/C/D/F/G/H: 记录响应时间和错误
	apiDuration := time.Since(beforeAPICall)
	totalDuration := time.Since(startTime)
	if err != nil {
		// 检查是否是 context 取消导致的
		ctxErr := ctx.Err()
		deadline, hasDeadline := ctx.Deadline()
		remainingTime := time.Duration(0)
		if hasDeadline {
			remainingTime = time.Until(deadline)
		}
		logger.Error("[DEBUG-A/B/C/D/F/G/H] LLM API failed - apiDuration: %.2fs, totalDuration: %.2fs, ctxErr: %v, hasDeadline: %v, remainingTime: %.2fs, error: %s",
			apiDuration.Seconds(), totalDuration.Seconds(), ctxErr, hasDeadline, remainingTime.Seconds(), err.Error())
		logger.Error("failed to create chat completion: %s, chatReq: %+v", err.Error(), chatReq)
		return nil, &ProviderError{
			Provider: p.Name(),
			Message:  "failed to create chat completion",
			Err:      err,
		}
	}
	logger.Info("[DEBUG-A/B/C/D/F/G/H] LLM API succeeded - apiDuration: %.2fs, totalDuration: %.2fs, choices: %d",
		apiDuration.Seconds(), totalDuration.Seconds(), len(resp.Choices))
	// #endregion

	if len(resp.Choices) == 0 {
		return nil, &ProviderError{
			Provider: p.Name(),
			Message:  "no choices in response",
		}
	}

	choice := resp.Choices[0]

	// 转换响应
	result := &ChatResponse{
		Content:      choice.Message.Content,
		FinishReason: string(choice.FinishReason),
	}

	// 转换工具调用
	if len(choice.Message.ToolCalls) > 0 {
		result.ToolCalls = make([]ToolCall, 0, len(choice.Message.ToolCalls))
		for _, tc := range choice.Message.ToolCalls {
			result.ToolCalls = append(result.ToolCalls, ToolCall{
				ID:   tc.ID,
				Type: string(tc.Type),
				Function: FunctionCall{
					Name:      tc.Function.Name,
					Arguments: tc.Function.Arguments,
				},
			})
		}
	}

	return result, nil
}

// Embedding 创建文本嵌入向量
// 示例用法：
//
//	provider := NewBkAiDevProvider("your_app_code", "your_app_secret")
//	result, err := provider.Embedding(ctx, "hunyuan-embedding", []string{"我是中国人,我爱我的祖国"})
func (p *OpenAIProvider) Embedding(ctx context.Context, model string, input []string) ([]openai.Embedding, error) {
	if model == "" {
		model = "hunyuan-embedding"
	}

	req := openai.EmbeddingRequest{
		Model: openai.EmbeddingModel(model),
		Input: input,
	}

	resp, err := p.client.CreateEmbeddings(ctx, req)
	if err != nil {
		return nil, &ProviderError{
			Provider: p.Name(),
			Message:  "failed to create embeddings",
			Err:      err,
		}
	}

	return resp.Data, nil
}

// AzureOpenAIProvider Azure OpenAI 提供商实现
type AzureOpenAIProvider struct {
	client      *openai.Client
	model       string
	maxTokens   int
	temperature float32
}

// AzureOpenAIConfig Azure OpenAI 配置
type AzureOpenAIConfig struct {
	APIKey      string  `yaml:"api_key" mapstructure:"api_key"`
	Endpoint    string  `yaml:"endpoint" mapstructure:"endpoint"`
	Deployment  string  `yaml:"deployment" mapstructure:"deployment"`
	APIVersion  string  `yaml:"api_version" mapstructure:"api_version"`
	MaxTokens   int     `yaml:"max_tokens" mapstructure:"max_tokens"`
	Temperature float32 `yaml:"temperature" mapstructure:"temperature"`
}

// NewAzureOpenAIProvider 创建 Azure OpenAI 提供商
func NewAzureOpenAIProvider(cfg AzureOpenAIConfig) *AzureOpenAIProvider {
	config := openai.DefaultAzureConfig(cfg.APIKey, cfg.Endpoint)
	if cfg.APIVersion != "" {
		config.APIVersion = cfg.APIVersion
	}

	client := openai.NewClientWithConfig(config)

	maxTokens := cfg.MaxTokens
	if maxTokens == 0 {
		maxTokens = 4096
	}

	temperature := cfg.Temperature
	if temperature == 0 {
		temperature = 0.3
	}

	return &AzureOpenAIProvider{
		client:      client,
		model:       cfg.Deployment,
		maxTokens:   maxTokens,
		temperature: temperature,
	}
}

// Name 返回提供商名称
func (p *AzureOpenAIProvider) Name() string {
	return "azure_openai"
}

// Chat 发送聊天请求
func (p *AzureOpenAIProvider) Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
	// 转换消息格式
	messages := make([]openai.ChatCompletionMessage, 0, len(req.Messages))
	for _, msg := range req.Messages {
		chatMsg := openai.ChatCompletionMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}

		if len(msg.ToolCalls) > 0 {
			toolCalls := make([]openai.ToolCall, 0, len(msg.ToolCalls))
			for _, tc := range msg.ToolCalls {
				toolCalls = append(toolCalls, openai.ToolCall{
					ID:   tc.ID,
					Type: openai.ToolType(tc.Type),
					Function: openai.FunctionCall{
						Name:      tc.Function.Name,
						Arguments: tc.Function.Arguments,
					},
				})
			}
			chatMsg.ToolCalls = toolCalls
		}

		if msg.ToolCallID != "" {
			chatMsg.ToolCallID = msg.ToolCallID
			chatMsg.Name = msg.Name
		}

		messages = append(messages, chatMsg)
	}

	var tools []openai.Tool
	if len(req.Tools) > 0 {
		tools = make([]openai.Tool, 0, len(req.Tools))
		for _, tool := range req.Tools {
			tools = append(tools, openai.Tool{
				Type: openai.ToolTypeFunction,
				Function: &openai.FunctionDefinition{
					Name:        tool.Function.Name,
					Description: tool.Function.Description,
					Parameters:  tool.Function.Parameters,
				},
			})
		}
	}

	chatReq := openai.ChatCompletionRequest{
		Model:       p.model,
		Messages:    messages,
		MaxTokens:   p.maxTokens,
		Temperature: p.temperature,
	}

	if len(tools) > 0 {
		chatReq.Tools = tools
	}
	logger.Info("chatReq: %+v", chatReq)
	resp, err := p.client.CreateChatCompletion(ctx, chatReq)
	if err != nil {
		logger.Error("failed to create chat completion: %s", err.Error())
		return nil, &ProviderError{
			Provider: p.Name(),
			Message:  "failed to create chat completion",
			Err:      err,
		}
	}

	if len(resp.Choices) == 0 {
		return nil, &ProviderError{
			Provider: p.Name(),
			Message:  "no choices in response",
		}
	}

	choice := resp.Choices[0]

	result := &ChatResponse{
		Content:      choice.Message.Content,
		FinishReason: string(choice.FinishReason),
	}

	if len(choice.Message.ToolCalls) > 0 {
		result.ToolCalls = make([]ToolCall, 0, len(choice.Message.ToolCalls))
		for _, tc := range choice.Message.ToolCalls {
			result.ToolCalls = append(result.ToolCalls, ToolCall{
				ID:   tc.ID,
				Type: string(tc.Type),
				Function: FunctionCall{
					Name:      tc.Function.Name,
					Arguments: tc.Function.Arguments,
				},
			})
		}
	}

	return result, nil
}

// CreateProvider 根据配置创建 LLM 提供商
func CreateProvider(providerType string, openaiCfg OpenAIConfig, azureCfg AzureOpenAIConfig) (LLMProvider, error) {
	switch providerType {
	case "bk_ai":
		return NewBkAiDevProvider(config.AppConfig.LLM.BkAi.AppCode, config.AppConfig.LLM.BkAi.AppSecret), nil
	case "openai":
		return NewOpenAIProvider(openaiCfg), nil
	case "azure", "azure_openai":
		return NewAzureOpenAIProvider(azureCfg), nil
	default:
		return nil, fmt.Errorf("unsupported provider type: %s", providerType)
	}
}
