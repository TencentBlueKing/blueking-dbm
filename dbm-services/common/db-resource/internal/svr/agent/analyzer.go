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
	"strings"
	"sync"
	"time"

	"gorm.io/gorm"

	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/go-pubpkg/logger"
)

// AnalysisResult 分析结果
type AnalysisResult struct {
	Summary      string            `json:"summary"`
	Reasons      []FailureReason   `json:"reasons"`
	Suggestions  []Suggestion      `json:"suggestions"`
	Verification *VerificationInfo `json:"verification,omitempty"`
	Duration     string            `json:"duration"`
	RawResponse  string            `json:"raw_response,omitempty"`
	MarkdownText string            `json:"markdown_text,omitempty"`
}

// FailureReason 失败原因
type FailureReason struct {
	Category    string      `json:"category"` // spec/disk/label/rstype/location/affinity
	Description string      `json:"description"`
	Impact      string      `json:"impact"` // high/medium/low
	Data        interface{} `json:"data,omitempty"`
}

// SuggestionType 建议类型（枚举）
type SuggestionType string

const (
	// 允许的建议类型
	SuggestionAddResources SuggestionType = "add_resources" // 补充资源
	SuggestionAdjustSpec   SuggestionType = "adjust_spec"   // 调整规格（如CPU/内存有弹性空间）
	SuggestionAddLabels    SuggestionType = "add_labels"    // 添加标签匹配
	SuggestionChangeRsType SuggestionType = "change_rstype" // 指定资源类型
	SuggestionAdjustDisk   SuggestionType = "adjust_disk"   // 调整磁盘要求
	SuggestionContactAdmin SuggestionType = "contact_admin" // 联系管理员

	// 禁止的建议类型（代码层面定义，用于过滤）
	forbiddenReduceCount    = "reduce_count"
	forbiddenReduceRequest  = "reduce_request"
	forbiddenRelaxAffinity  = "relax_affinity"
	forbiddenSplitRequest   = "split_request"
	forbiddenLowerQuantity  = "lower_quantity"
	forbiddenChangeLocation = "change_location" // 更换地域是业务基本需求，禁止建议
)

// Suggestion 建议
type Suggestion struct {
	Type           string `json:"type"`
	Description    string `json:"description"`
	PredictedCount int    `json:"predicted_count,omitempty"`
	Verified       bool   `json:"verified"`
	Priority       int    `json:"priority"`
}

// IsForbiddenSuggestion 检查是否为禁止的建议类型
func IsForbiddenSuggestion(suggestionType string) bool {
	forbiddenTypes := []string{
		forbiddenReduceCount,
		forbiddenReduceRequest,
		forbiddenRelaxAffinity,
		forbiddenSplitRequest,
		forbiddenLowerQuantity,
		forbiddenChangeLocation, // 更换地域是业务基本需求，禁止建议
	}
	for _, t := range forbiddenTypes {
		if suggestionType == t {
			return true
		}
	}
	return false
}

// FilterSuggestions 过滤掉禁止的建议
func FilterSuggestions(suggestions []Suggestion) []Suggestion {
	filtered := make([]Suggestion, 0, len(suggestions))
	for _, s := range suggestions {
		if !IsForbiddenSuggestion(s.Type) {
			filtered = append(filtered, s)
		}
	}
	return filtered
}

// VerificationInfo 验证信息
type VerificationInfo struct {
	AllVerified bool   `json:"all_verified"`
	Confidence  string `json:"confidence"` // high/medium/low
}

// ResourceAnalyzer 资源分析器
type ResourceAnalyzer struct {
	executor *AgentExecutor
	enabled  bool
	mu       sync.RWMutex
}

var (
	globalAnalyzer *ResourceAnalyzer
	analyzerOnce   sync.Once
)

// InitAnalyzer 初始化全局分析器
func InitAnalyzer(db *gorm.DB, cfg *LLMConfig) error {
	if cfg == nil || !cfg.Enabled {
		logger.Info("[Analyzer] LLM analysis is disabled")
		return nil
	}

	var initErr error
	analyzerOnce.Do(func() {
		// 创建 LLM Provider
		provider, err := CreateProvider(cfg.Provider, cfg.OpenAI, cfg.Azure)
		if err != nil {
			initErr = fmt.Errorf("failed to create LLM provider: %v", err)
			return
		}

		// 创建工具集
		tools := NewResourceTools(db)

		// 创建执行器
		executor := NewAgentExecutor(provider, tools, cfg.Agent)

		globalAnalyzer = &ResourceAnalyzer{
			executor: executor,
			enabled:  true,
		}

		logger.Info("[Analyzer] LLM analyzer initialized with provider: %s", provider.Name())
	})

	return initErr
}

// GetAnalyzer 获取全局分析器
func GetAnalyzer() *ResourceAnalyzer {
	return globalAnalyzer
}

// IsEnabled 检查是否启用
func (a *ResourceAnalyzer) IsEnabled() bool {
	if a == nil {
		return false
	}
	a.mu.RLock()
	defer a.mu.RUnlock()
	return a.enabled
}

// Analyze 分析资源匹配失败原因
func (a *ResourceAnalyzer) Analyze(ctx context.Context, applyParams *apply.RequestInputParam) (*AnalysisResult, error) {
	if !a.IsEnabled() {
		return nil, fmt.Errorf("LLM analyzer is not enabled")
	}

	startTime := time.Now()

	// 构建消息
	systemPrompt := GetSystemPrompt()
	userMessage := BuildUserMessage(applyParams)

	// 执行 Agent
	execResult, err := a.executor.Execute(ctx, systemPrompt, userMessage)
	if err != nil {
		logger.Error("[Analyzer] Agent execution failed: %v", err)
		return nil, err
	}

	// 解析结果
	result := &AnalysisResult{
		Duration:    time.Since(startTime).String(),
		RawResponse: execResult.FinalResponse,
	}

	// 尝试解析 JSON 响应
	if err := a.parseResponse(execResult.FinalResponse, result); err != nil {
		logger.Warn("[Analyzer] Failed to parse JSON response, using raw response: %v", err)
		result.Summary = execResult.FinalResponse
	}

	logger.Info("[Analyzer] Analysis completed in %s, iterations: %d, tool calls: %d",
		result.Duration, execResult.Iterations, len(execResult.ToolCalls))

	// 后处理：将园区 ID 转换为友好的显示格式
	formatAnalysisResult(result)

	// 如果 LLM 没有返回 Markdown 格式，使用备用格式化函数生成
	if result.MarkdownText == "" {
		logger.Info("[Analyzer] No Markdown from LLM, generating from JSON data")
		result.MarkdownText = FormatAnalysisResultToMarkdown(result)
	}

	return result, nil
}

// parseResponse 解析 LLM 响应
func (a *ResourceAnalyzer) parseResponse(response string, result *AnalysisResult) error {
	// 检查是否包含 Markdown 分隔符
	markdownSeparator := "---MARKDOWN---"
	markdownStartIdx := strings.Index(response, markdownSeparator)

	var jsonPart string
	if markdownStartIdx != -1 {
		// 提取 JSON 部分（分隔符之前）
		jsonPart = response[:markdownStartIdx]
		// 提取 Markdown 部分（分隔符之后）
		markdownPart := strings.TrimSpace(response[markdownStartIdx+len(markdownSeparator):])
		result.MarkdownText = markdownPart
		logger.Info("[Analyzer] Found Markdown section, length: %d", len(markdownPart))
	} else {
		// 没有分隔符，整个响应都是 JSON
		jsonPart = response
		logger.Info("[Analyzer] No Markdown separator found, will generate Markdown later")
	}

	// 尝试从响应中提取 JSON
	jsonStr := extractJSON(jsonPart)
	if jsonStr == "" {
		logger.Warn("[Analyzer] No JSON found in response, response length: %d", len(jsonPart))
		return fmt.Errorf("no JSON found in response")
	}

	logger.Info("[Analyzer] Extracted JSON length: %d", len(jsonStr))

	var parsed struct {
		Summary      string            `json:"summary"`
		Reasons      []FailureReason   `json:"reasons"`
		Suggestions  []Suggestion      `json:"suggestions"`
		Verification *VerificationInfo `json:"verification"`
	}

	if err := json.Unmarshal([]byte(jsonStr), &parsed); err != nil {
		logger.Error("[Analyzer] JSON unmarshal failed: %v, JSON: %s", err, jsonStr[:min(500, len(jsonStr))])
		return err
	}

	result.Summary = parsed.Summary
	result.Reasons = parsed.Reasons
	// 过滤掉禁止的建议类型
	result.Suggestions = FilterSuggestions(parsed.Suggestions)
	result.Verification = parsed.Verification

	logger.Info("[Analyzer] Parsed successfully: summary=%s, reasons=%d, suggestions=%d",
		parsed.Summary[:min(50, len(parsed.Summary))], len(parsed.Reasons), len(parsed.Suggestions))

	return nil
}

// min 返回两个整数中的较小值
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// extractJSON 从文本中提取 JSON
func extractJSON(text string) string {
	// 先尝试去除 markdown 代码块
	text = stripMarkdownCodeBlock(text)

	// 查找第一个 { 和最后一个 }
	start := -1
	end := -1
	depth := 0

	for i, c := range text {
		if c == '{' {
			if start == -1 {
				start = i
			}
			depth++
		} else if c == '}' {
			depth--
			if depth == 0 {
				end = i + 1
				break
			}
		}
	}

	if start != -1 && end != -1 && start < end {
		return text[start:end]
	}

	return ""
}

// stripMarkdownCodeBlock 去除 markdown 代码块标记
func stripMarkdownCodeBlock(text string) string {
	// 处理 ```json ... ``` 或 ``` ... ``` 格式
	text = strings.TrimSpace(text)

	// 检查是否以 ``` 开头
	if strings.HasPrefix(text, "```") {
		// 找到第一个换行符（跳过 ```json 或 ```）
		firstNewline := strings.Index(text, "\n")
		if firstNewline != -1 {
			text = text[firstNewline+1:]
		}

		// 找到最后一个 ```
		lastBackticks := strings.LastIndex(text, "```")
		if lastBackticks != -1 {
			text = text[:lastBackticks]
		}
	}

	return strings.TrimSpace(text)
}

// LLMConfig LLM 配置
type LLMConfig struct {
	Enabled  bool              `yaml:"enabled" mapstructure:"enabled"`
	Provider string            `yaml:"provider" mapstructure:"provider"`
	OpenAI   OpenAIConfig      `yaml:"openai" mapstructure:"openai"`
	Azure    AzureOpenAIConfig `yaml:"azure" mapstructure:"azure"`
	Agent    AgentConfig       `yaml:"agent" mapstructure:"agent"`
}

// KnownFailReason 已知失败原因（从匹配流程中获取）
type KnownFailReason struct {
	Category    string                 `json:"category"`    // affinity/spec/disk/label/rstype/location
	Type        string                 `json:"type"`        // 具体类型，如 cross_rack/cross_switch
	Description string                 `json:"description"` // 描述
	Data        map[string]interface{} `json:"data"`        // 相关数据
}

// KnownAffinityDistribution 已知的亲和性分布（从匹配流程中获取）
type KnownAffinityDistribution struct {
	AffinityType     string                    `json:"affinity_type"`
	AvailableCount   int                       `json:"available_count"`
	RequestCount     int                       `json:"request_count"`
	UniqueSubZones   int                       `json:"unique_subzones"`
	UniqueRacks      int                       `json:"unique_racks"`
	UniqueNetDevices int                       `json:"unique_net_devices"`
	BySubZone        map[string]int            `json:"by_subzone"`
	ByRack           map[string]int            `json:"by_rack"`
	ByNetDevice      map[string]int            `json:"by_net_device"`
	RacksBySubZone   map[string]map[string]int `json:"racks_by_subzone"` // 每个园区内的机架分布
}

// AnalysisContext 分析上下文，包含申请参数和已知的失败原因
type AnalysisContext struct {
	ApplyParams          *apply.RequestInputParam   `json:"apply_params"`
	KnownFailReasons     []KnownFailReason          `json:"known_fail_reasons,omitempty"`
	AffinityDistribution *KnownAffinityDistribution `json:"affinity_distribution,omitempty"`
}

// AnalyzeApplyFailure 分析申请失败（便捷方法）
func AnalyzeApplyFailure(ctx context.Context, applyParams *apply.RequestInputParam) (*AnalysisResult, error) {
	analyzer := GetAnalyzer()
	if analyzer == nil || !analyzer.IsEnabled() {
		return nil, nil
	}

	return analyzer.Analyze(ctx, applyParams)
}

// AnalyzeWithContext 使用上下文分析申请失败（包含已知原因）
func AnalyzeWithContext(ctx context.Context, analysisCtx *AnalysisContext) (*AnalysisResult, error) {
	analyzer := GetAnalyzer()
	if analyzer == nil || !analyzer.IsEnabled() {
		return nil, nil
	}

	return analyzer.AnalyzeWithKnownReasons(ctx, analysisCtx)
}

// AnalyzeWithKnownReasons 使用已知原因分析
func (a *ResourceAnalyzer) AnalyzeWithKnownReasons(ctx context.Context, analysisCtx *AnalysisContext) (*AnalysisResult, error) {
	if !a.IsEnabled() {
		return nil, fmt.Errorf("LLM analyzer is not enabled")
	}

	startTime := time.Now()

	// 构建消息，包含已知原因
	systemPrompt := GetSystemPromptWithKnownReasons(analysisCtx.KnownFailReasons, analysisCtx.AffinityDistribution)
	userMessage := BuildUserMessageWithContext(analysisCtx)

	// 执行 Agent
	execResult, err := a.executor.Execute(ctx, systemPrompt, userMessage)
	if err != nil {
		logger.Error("[Analyzer] Agent execution failed: %v", err)
		return nil, err
	}

	// 解析结果
	result := &AnalysisResult{
		Duration:    time.Since(startTime).String(),
		RawResponse: execResult.FinalResponse,
	}

	// 尝试解析 JSON 响应
	if err := a.parseResponse(execResult.FinalResponse, result); err != nil {
		logger.Warn("[Analyzer] Failed to parse JSON response, using raw response: %v", err)
		result.Summary = execResult.FinalResponse
	}

	logger.Info("[Analyzer] Analysis completed in %s, iterations: %d, tool calls: %d",
		result.Duration, execResult.Iterations, len(execResult.ToolCalls))

	// 后处理：将园区 ID 转换为友好的显示格式
	formatAnalysisResult(result)

	// 如果 LLM 没有返回 Markdown 格式，使用备用格式化函数生成
	if result.MarkdownText == "" {
		logger.Info("[Analyzer] No Markdown from LLM, generating from JSON data")
		result.MarkdownText = FormatAnalysisResultToMarkdown(result)
	}

	return result, nil
}

// BuildUserMessageWithContext 构建包含已知原因的用户消息
func BuildUserMessageWithContext(analysisCtx *AnalysisContext) string {
	paramsJSON, _ := json.MarshalIndent(analysisCtx.ApplyParams, "", "  ")
	message := fmt.Sprintf("请分析以下资源申请失败的原因：\n\n申请参数：\n```json\n%s\n```\n", string(paramsJSON))

	// 如果有已知的失败原因，添加到消息中
	if len(analysisCtx.KnownFailReasons) > 0 {
		message += "\n## 已确定的失败原因（来自匹配流程）\n\n"
		for i, reason := range analysisCtx.KnownFailReasons {
			message += fmt.Sprintf("%d. **%s** (%s): %s\n", i+1, reason.Category, reason.Type, reason.Description)
			if len(reason.Data) > 0 {
				dataJSON, _ := json.MarshalIndent(reason.Data, "   ", "  ")
				message += fmt.Sprintf("   数据: %s\n", string(dataJSON))
			}
		}
	}

	// 如果有亲和性分布信息，添加到消息中
	if analysisCtx.AffinityDistribution != nil {
		dist := analysisCtx.AffinityDistribution
		message += fmt.Sprintf("\n## 已确定的资源分布（来自匹配流程）\n\n")
		message += fmt.Sprintf("- 亲和性类型: %s\n", dist.AffinityType)
		message += fmt.Sprintf("- 可用资源数: %d\n", dist.AvailableCount)
		message += fmt.Sprintf("- 申请数量: %d\n", dist.RequestCount)
		message += fmt.Sprintf("- 不同园区数: %d\n", dist.UniqueSubZones)
		message += fmt.Sprintf("- 不同机架数: %d\n", dist.UniqueRacks)
		message += fmt.Sprintf("- 不同交换机数: %d\n", dist.UniqueNetDevices)

		if len(dist.BySubZone) > 0 {
			message += "\n### 按园区分布\n"
			for subzone, count := range dist.BySubZone {
				message += fmt.Sprintf("- %s: %d 台\n", subzone, count)
			}
		}
		if len(dist.RacksBySubZone) > 0 {
			message += "\n### 各园区内机架分布\n"
			for subzone, racks := range dist.RacksBySubZone {
				message += fmt.Sprintf("**%s** (共%d个机架):\n", subzone, len(racks))
				for rack, count := range racks {
					message += fmt.Sprintf("  - %s: %d 台\n", rack, count)
				}
			}
		}
		if len(dist.ByNetDevice) > 0 {
			message += "\n### 按交换机分布\n"
			for netDevice, count := range dist.ByNetDevice {
				message += fmt.Sprintf("- %s: %d 台\n", netDevice, count)
			}
		}
	}

	return message
}

// QuickAnalysis 快速分析（不使用 LLM，仅使用规则）
type QuickAnalysis struct {
	tools *ResourceTools
}

// NewQuickAnalysis 创建快速分析器
func NewQuickAnalysis(db *gorm.DB) *QuickAnalysis {
	return &QuickAnalysis{
		tools: NewResourceTools(db),
	}
}

// QuickAnalysisResult 快速分析结果
type QuickAnalysisResult struct {
	PoolStats        *PoolStats              `json:"pool_stats,omitempty"`
	ConditionCheck   *MatchConditionsResult  `json:"condition_check,omitempty"`
	DiskAnalysis     *DiskAnalysisResult     `json:"disk_analysis,omitempty"`
	LabelAnalysis    *LabelAnalysisResult    `json:"label_analysis,omitempty"`
	RsTypeAnalysis   *RsTypeAnalysisResult   `json:"rstype_analysis,omitempty"`
	AffinityAnalysis *AffinityAnalysisResult `json:"affinity_analysis,omitempty"`
}

// Analyze 执行快速分析
func (q *QuickAnalysis) Analyze(params map[string]interface{}) (*QuickAnalysisResult, error) {
	result := &QuickAnalysisResult{}

	// 1. 查询资源池统计
	if poolStats, err := q.tools.QueryPoolStats(params); err == nil {
		result.PoolStats = poolStats
	}

	// 2. 检查匹配条件
	var finalAvailableCount int
	var requestCount int
	if condCheck, err := q.tools.CheckMatchConditions(params); err == nil {
		result.ConditionCheck = condCheck
		finalAvailableCount = condCheck.FinalCount
		requestCount = condCheck.RequestCount
	}

	// 3. 磁盘分析
	if _, hasDisk := params["disk_mount_point"]; hasDisk {
		if diskAnalysis, err := q.tools.AnalyzeDiskIssues(params); err == nil {
			result.DiskAnalysis = diskAnalysis
		}
	}

	// 4. 标签分析
	if labelAnalysis, err := q.tools.AnalyzeLabelIssues(params); err == nil {
		result.LabelAnalysis = labelAnalysis
	}

	// 5. 资源类型分析
	if rsTypeAnalysis, err := q.tools.AnalyzeRsTypeIssues(params); err == nil {
		result.RsTypeAnalysis = rsTypeAnalysis
	}

	// 6. 亲和性分析
	// 重要：只有当基础条件筛选后资源数量 >= 申请数量时，才分析亲和性
	// 如果基础条件就不满足，亲和性分析没有意义，因为瓶颈不在亲和性
	if affinityType, ok := params["affinity_type"].(string); ok && affinityType != "" {
		// 只有资源数量足够时才需要分析亲和性问题
		if finalAvailableCount >= requestCount {
			if affinityAnalysis, err := q.tools.AnalyzeAffinityIssues(params); err == nil {
				result.AffinityAnalysis = affinityAnalysis
			}
		}
		// 如果资源数量本身就不足，跳过亲和性分析，聚焦基础条件问题
	}

	return result, nil
}

// formatAnalysisResult 对分析结果进行后处理，将园区 ID 转换为友好的显示格式
// 这个函数在返回分析结果给用户之前调用，确保用户看到的是友好的园区名称而不是原始 ID
func formatAnalysisResult(result *AnalysisResult) {
	if result == nil {
		return
	}

	// 格式化 Summary
	result.Summary = FormatSubZoneIDsInText(result.Summary)

	// 格式化 RawResponse
	result.RawResponse = FormatSubZoneIDsInText(result.RawResponse)

	// 格式化 Reasons
	for i := range result.Reasons {
		result.Reasons[i].Description = FormatSubZoneIDsInText(result.Reasons[i].Description)
		// Data 是 interface{} 类型，需要处理字符串情况
		if dataStr, ok := result.Reasons[i].Data.(string); ok {
			result.Reasons[i].Data = FormatSubZoneIDsInText(dataStr)
		}
	}

	// 格式化 Suggestions
	for i := range result.Suggestions {
		result.Suggestions[i].Description = FormatSubZoneIDsInText(result.Suggestions[i].Description)
	}
}
