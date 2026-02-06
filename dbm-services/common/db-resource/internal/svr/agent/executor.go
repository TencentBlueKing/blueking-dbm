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
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/go-pubpkg/logger"
)

// AgentExecutor Agent 执行器
type AgentExecutor struct {
	provider      LLMProvider
	tools         *ResourceTools
	maxIterations int
	timeout       time.Duration
}

// AgentConfig Agent 配置
type AgentConfig struct {
	MaxIterations  int `yaml:"max_iterations" mapstructure:"max_iterations"`
	TimeoutSeconds int `yaml:"timeout_seconds" mapstructure:"timeout_seconds"`
}

// NewAgentExecutor 创建 Agent 执行器
func NewAgentExecutor(provider LLMProvider, tools *ResourceTools, cfg AgentConfig) *AgentExecutor {
	maxIterations := cfg.MaxIterations
	if maxIterations <= 0 {
		maxIterations = 15
	}

	timeout := time.Duration(cfg.TimeoutSeconds) * time.Second
	if timeout <= 0 {
		timeout = LLMAnalysisTimeout
	}

	return &AgentExecutor{
		provider:      provider,
		tools:         tools,
		maxIterations: maxIterations,
		timeout:       timeout,
	}
}

// ExecutionResult Agent 执行结果
type ExecutionResult struct {
	Success       bool          `json:"success"`
	FinalResponse string        `json:"final_response"`
	Iterations    int           `json:"iterations"`
	ToolCalls     []ToolCallLog `json:"tool_calls"`
	Duration      time.Duration `json:"duration"`
	Error         string        `json:"error,omitempty"`
}

// ToolCallLog 工具调用日志
type ToolCallLog struct {
	Iteration int         `json:"iteration"`
	ToolName  string      `json:"tool_name"`
	Arguments string      `json:"arguments"`
	Result    interface{} `json:"result"`
	Error     string      `json:"error,omitempty"`
}

// Execute 执行 Agent
func (e *AgentExecutor) Execute(ctx context.Context, systemPrompt, userMessage string) (*ExecutionResult, error) {
	startTime := time.Now()

	// #region agent log - 假设 B: 记录 Agent Executor 超时配置
	logger.Info("[DEBUG-B] Agent Execute started - timeout: %.2fs, maxIterations: %d",
		e.timeout.Seconds(), e.maxIterations)
	// #endregion

	// 设置超时
	ctx, cancel := context.WithTimeout(ctx, e.timeout)
	defer cancel()

	result := &ExecutionResult{
		ToolCalls: make([]ToolCallLog, 0),
	}

	// 初始化消息
	messages := []Message{
		NewSystemMessage(systemPrompt),
		NewUserMessage(userMessage),
	}

	// 获取工具定义
	toolDefs := e.tools.GetToolDefinitions()

	// 推理循环
	for iteration := 1; iteration <= e.maxIterations; iteration++ {
		result.Iterations = iteration

		// 检查上下文是否已取消
		select {
		case <-ctx.Done():
			result.Error = "execution timeout"
			result.Duration = time.Since(startTime)
			return result, ctx.Err()
		default:
		}

		logger.Info("[Agent] Iteration %d/%d, messages count: %d",
			iteration, e.maxIterations, len(messages))

		// #region agent log - 假设 B/E: 记录每次迭代的剩余超时时间
		deadline, _ := ctx.Deadline()
		remainingTimeout := time.Until(deadline)
		logger.Info("[DEBUG-B/E] Before Chat call - iteration: %d, remainingTimeout: %.2fs, elapsedTotal: %.2fs",
			iteration, remainingTimeout.Seconds(), time.Since(startTime).Seconds())
		// #endregion

		// 调用 LLM
		chatReq := &ChatRequest{
			Messages: messages,
			Tools:    toolDefs,
		}

		resp, err := e.provider.Chat(ctx, chatReq)
		if err != nil {
			// #region agent log - 假设 E: 记录失败时的详细信息
			logger.Error("[DEBUG-E] Chat failed - iteration: %d, error: %v, elapsedTotal: %.2fs",
				iteration, err, time.Since(startTime).Seconds())
			// #endregion
			result.Error = fmt.Sprintf("LLM chat failed: %v", err)
			result.Duration = time.Since(startTime)
			return result, err
		}

		// 检查是否有工具调用
		if resp.HasToolCalls() {
			// 添加 assistant 消息（包含工具调用）
			messages = append(messages, NewAssistantToolCallMessage(resp.ToolCalls))

			// 执行工具调用
			var earlyExitResponse string
			for _, toolCall := range resp.ToolCalls {
				logger.Info("[Agent] Calling tool: %s, args: %s",
					toolCall.Function.Name, toolCall.Function.Arguments)

				toolResult, toolErr := e.tools.ExecuteTool(
					toolCall.Function.Name,
					toolCall.Function.Arguments,
				)

				callLog := ToolCallLog{
					Iteration: iteration,
					ToolName:  toolCall.Function.Name,
					Arguments: toolCall.Function.Arguments,
					Result:    toolResult,
				}

				if toolErr != nil {
					callLog.Error = toolErr.Error()
					logger.Error("[Agent] Tool %s error: %v", toolCall.Function.Name, toolErr)
					// 将错误信息作为工具结果返回给 LLM
					toolResult = map[string]string{"error": toolErr.Error()}
				}

				result.ToolCalls = append(result.ToolCalls, callLog)

				// 添加工具结果消息
				messages = append(messages, NewToolResultMessage(
					toolCall.ID,
					toolCall.Function.Name,
					toolResult,
				))

				// 硬性条件不满足时提前结束：不继续分析亲和性等问题
				if toolErr == nil {
					switch toolCall.Function.Name {
					case "analyze_disk_issues", "analyze_label_issues", "analyze_rstype_issues":
						// 磁盘/标签/资源类型已确定是根因时，无需再分析亲和性
						if exitResp := trySpecConditionEarlyExit(toolCall.Function.Name, toolResult); exitResp != "" {
							earlyExitResponse = exitResp
						}
					}
				}
			}

			if earlyExitResponse != "" {
				result.Success = true
				result.FinalResponse = earlyExitResponse
				result.Duration = time.Since(startTime)
				logger.Info("[Agent] Early exit: root cause identified (disk/label/rstype/spec), skip affinity analysis after %d iterations", iteration)
				return result, nil
			}

			// 继续下一轮
			continue
		}

		// 没有工具调用，检查是否完成
		if resp.FinishReason == "stop" || resp.Content != "" {
			result.Success = true
			result.FinalResponse = resp.Content
			result.Duration = time.Since(startTime)
			logger.Info("[Agent] Completed after %d iterations", iteration)
			return result, nil
		}
	}

	// 达到最大迭代次数
	result.Error = fmt.Sprintf("max iterations (%d) reached", e.maxIterations)
	result.Duration = time.Since(startTime)

	// 尝试获取最后的内容
	if len(messages) > 0 {
		lastMsg := messages[len(messages)-1]
		if lastMsg.Role == "assistant" && lastMsg.Content != "" {
			result.FinalResponse = lastMsg.Content
		}
	}

	return result, nil
}

// tryHardConditionEarlyExit 检查硬性条件是否不满足，若不满足则生成提前结束的响应
// 硬性条件不满足时（base_count==0 或 final_count<request_count），不应继续分析亲和性问题
func (e *AgentExecutor) tryHardConditionEarlyExit(toolResult interface{}) string {
	mc, ok := toolResult.(*MatchConditionsResult)
	if !ok {
		return ""
	}
	// 硬性条件不满足：基础资源为0，或最终可用资源少于申请数量
	if mc.BaseCount == 0 || mc.FinalCount < mc.RequestCount {
		return buildHardConditionEarlyExitResponse(mc)
	}
	return ""
}

// buildHardConditionEarlyExitResponse 构建硬性条件不满足时的提前结束响应
func buildHardConditionEarlyExitResponse(mc *MatchConditionsResult) string {
	summary := mc.RootCause
	if summary == "" {
		summary = mc.Summary
	}
	if summary == "" {
		summary = fmt.Sprintf("需要 %d 台资源，但仅满足硬性条件的资源为 %d 台，缺少 %d 台",
			mc.RequestCount, mc.FinalCount, mc.RequestCount-mc.FinalCount)
	}

	reason := map[string]interface{}{
		"category":    "spec",
		"description": summary,
		"impact":      "high",
		"data":        fmt.Sprintf("base_count=%d, final_count=%d, request_count=%d", mc.BaseCount, mc.FinalCount, mc.RequestCount),
	}

	suggestions := []map[string]interface{}{
		{
			"type":            "add_resources",
			"description":     "建议补充满足条件的资源",
			"predicted_count": 0,
			"verified":        false,
			"priority":        1,
		},
	}
	if mc.BaseCount == 0 && mc.TotalTableCount == 0 {
		suggestions = []map[string]interface{}{
			{
				"type":            "contact_admin",
				"description":     "资源表为空，需要先导入资源数据",
				"predicted_count": 0,
				"verified":        false,
				"priority":        1,
			},
		}
	}

	resp := map[string]interface{}{
		"summary":     summary,
		"reasons":     []map[string]interface{}{reason},
		"suggestions": suggestions,
		"verification": map[string]interface{}{
			"all_verified": false,
			"confidence":   "high",
		},
	}
	data, err := json.MarshalIndent(resp, "", "  ")
	if err != nil {
		return fmt.Sprintf(`{"summary": %q, "reasons": [], "suggestions": []}`, summary)
	}
	return string(data)
}

// trySpecConditionEarlyExit 检查磁盘/标签/资源类型分析是否已确定根因，若是则生成提前结束的响应
// 当这些专项分析工具返回 IssueType 时，说明根因已明确，无需再分析亲和性
func trySpecConditionEarlyExit(toolName string, toolResult interface{}) string {
	var issueType, issueDetail, suggestion, category string
	switch toolName {
	case "analyze_disk_issues":
		dr, ok := toolResult.(*DiskAnalysisResult)
		if !ok || dr.IssueType == "" {
			return ""
		}
		issueType, issueDetail, suggestion, category = dr.IssueType, dr.IssueDetail, dr.Suggestion, "disk"
	case "analyze_label_issues":
		lr, ok := toolResult.(*LabelAnalysisResult)
		if !ok || lr.IssueType == "" {
			return ""
		}
		issueType, issueDetail, suggestion, category = lr.IssueType, lr.IssueDetail, lr.Suggestion, "label"
	case "analyze_rstype_issues":
		rr, ok := toolResult.(*RsTypeAnalysisResult)
		if !ok || rr.IssueType == "" {
			return ""
		}
		issueType, issueDetail, suggestion, category = rr.IssueType, rr.IssueDetail, rr.Suggestion, "rstype"
	default:
		return ""
	}
	return buildSpecConditionEarlyExitResponse(issueType, issueDetail, suggestion, category)
}

// buildSpecConditionEarlyExitResponse 构建磁盘/标签/资源类型根因确定时的提前结束响应
func buildSpecConditionEarlyExitResponse(issueType, issueDetail, suggestion, category string) string {
	summary := issueDetail
	if summary == "" {
		summary = issueType
	}

	reason := map[string]interface{}{
		"category":    category,
		"description": summary,
		"impact":      "high",
		"data":        issueType,
	}

	sugDesc := suggestion
	if sugDesc == "" {
		sugDesc = "建议根据上述问题调整申请条件或补充资源"
	}
	sugType := "adjust_disk"
	if category == "label" {
		sugType = "add_labels"
	} else if category == "rstype" {
		sugType = "change_rstype"
	}
	suggestions := []map[string]interface{}{
		{
			"type":            sugType,
			"description":     sugDesc,
			"predicted_count": 0,
			"verified":        false,
			"priority":        1,
		},
	}

	resp := map[string]interface{}{
		"summary":     summary,
		"reasons":     []map[string]interface{}{reason},
		"suggestions": suggestions,
		"verification": map[string]interface{}{
			"all_verified": false,
			"confidence":   "high",
		},
	}
	data, err := json.MarshalIndent(resp, "", "  ")
	if err != nil {
		return fmt.Sprintf(`{"summary": %q, "reasons": [], "suggestions": []}`, summary)
	}
	return string(data)
}

// GetSystemPrompt 获取系统提示词
func GetSystemPrompt() string {
	return `你是蓝鲸 DBM 资源管理系统的智能分析助手。你的任务是分析数据库资源申请失败的原因，并提供可行的解决建议。

## 可用工具

**重要：不要局限于预设工具，主动验证推测**

预设工具是起点，但当你对问题有推测时，应该主动使用 execute_custom_query 工具执行 SQL 查询来验证，而不是仅仅依赖预设工具的结果。

1. **query_pool_stats**: 查询资源池统计信息
   - 用于了解资源池的整体状况
   - 可按城市、园区、资源类型查看分布

2. **check_match_conditions**: 逐步检查匹配条件
   - 用于找出导致资源不足的关键瓶颈条件
   - 返回每个条件对资源数量的影响
   - **注意**：如果结果显示资源不足，不要立即下结论，主动查询验证

3. **analyze_disk_issues**: 分析磁盘匹配问题
   - **支持多块磁盘条件查询**：可以同时检查多个挂载点（如/data, /data1, /data2）
   - 使用 disk_specs 数组参数指定多磁盘条件
   - 检查挂载点是否存在
   - 检查磁盘类型(SSD/HDD/CLOUD_SSD等)是否匹配
   - 检查磁盘大小是否足够
   - 返回每个挂载点的详细匹配情况
   - **若确定磁盘是根因（返回 issue_type），系统会提前结束，无需再分析亲和性**

4. **analyze_label_issues**: 分析标签匹配问题
   - 检查无标签申请与有标签资源的冲突
   - 查看资源池中可用的标签
   - **若确定标签是根因（返回 issue_type），系统会提前结束，无需再分析亲和性**

5. **analyze_rstype_issues**: 分析资源类型匹配问题
   - 检查 PUBLIC 与专用类型的分布
   - 检测类型名称不一致问题
   - **重要**：PUBLIC 类型的资源可以匹配任何资源类型的申请
   - **若确定资源类型是根因（返回 issue_type），系统会提前结束，无需再分析亲和性**

6. **analyze_affinity_issues**: 分析亲和性匹配问题
   - **仅当硬性条件满足后**（base_count>0 且 final_count>=request_count）才使用此工具
   - 当资源数量足够但因跨机架/跨交换机分布不足时使用
   - 展示资源在机架和交换机上的详细分布
   - 检查亲和性约束是否满足
   - **若 check_match_conditions 或 disk/label/rstype 分析已确定根因，系统会提前结束，无需再调用此工具**

7. **verify_prediction**: 验证预测结果（**必须使用**）
   - **在给出建议后必须使用此工具验证每个建议的可行性**
   - 支持多磁盘条件验证
   - 返回详细的验证结果，包括是否验证通过、置信度等
   - 设置 request_count 参数可自动判断是否满足申请需求

8. **execute_custom_query**: 执行自定义 SQL 查询验证推测（**强烈推荐主动使用**）
   - **这是最重要的工具**：当你有任何推测或疑问时，主动使用此工具执行 SQL 查询来验证
   - 只能执行 SELECT 查询，只能查询 tb_rp_detail 表
   - 用于验证假设、检查数据分布、统计资源数量等
   - **重要规则**：PUBLIC 类型的资源可以匹配任何资源类型的申请。
     查询时应该使用 rs_type IN ('PUBLIC', '申请的资源类型')，而不是只匹配申请的资源类型
   - **使用场景**：
     - 验证资源总数是否足够：SELECT COUNT(*) FROM tb_rp_detail WHERE ... AND rs_type IN ('PUBLIC', 'redis')
     - 检查各园区分布：SELECT COUNT(*) as count, sub_zone_id FROM tb_rp_detail WHERE ... AND rs_type IN ('PUBLIC', 'redis') GROUP BY sub_zone_id
     - 检查各机架分布：SELECT COUNT(*) as count, rack_id FROM tb_rp_detail WHERE ... AND rs_type IN ('PUBLIC', 'redis') GROUP BY rack_id
     - 检查磁盘条件影响：对比含磁盘条件和不含磁盘条件的查询结果
     - 验证任何推测：不要等待工具结果，主动查询验证

## 多磁盘场景说明

storage_device 是一个 JSON 对象，支持多块磁盘存储：
{
  "/data": {"size": 100, "disk_type": "CLOUD_SSD", ...},
  "/data1": {"size": 200, "disk_type": "HDD", ...},
  "/data2": {"size": 300, "disk_type": "SSD", ...}
}

当申请参数中包含多个磁盘规格（storage_spec 数组）时，需要检查所有磁盘条件是否同时满足。

## 亲和性类型说明

- **NONE**: 无亲和性要求
- **SAME_SUBZONE**: 同城同园区，不要求跨机架跨交换机
- **SAME_SUBZONE_CROSS_SWTICH**: 同城同园区跨机架跨交换机，每台机器需在不同机架且不同交换机
- **CROSS_RACK**: 跨机架，每台机器需在不同机架
- **CROS_SUBZONE**: 同城跨园区
  - 支持自定义容忍度 tolerance（0-1）
  - TotalCount = 已有机器数 + 申请数量
  - MaxPerSubZone = ceil(TotalCount × tolerance)，即每个园区最多放多少台
  - 如果 tolerance=0，则 MaxPerSubZone=1，必须完全跨园区
  - 最少需要的园区数 = ceil(TotalCount / MaxPerSubZone)
  - 例：申请6台，tolerance=0.5 → MaxPerSubZone=3，需要至少2个园区
  - 例：申请6台，tolerance=0 → MaxPerSubZone=1，需要至少6个园区
- **CROSS_SUBZONE_STRONG**: 跨园区(强)
  - 园区容忍度1/3 → 至少需要3个园区
  - MaxPerSubZone = ceil(总数量 × 1/3)，即每个园区最多放总数的1/3
  - 机架容忍度1/2 → 每园区至少需要2个机架
  - MaxPerRack = ceil(MaxPerSubZone × 1/2)，即每个机架最多放园区限额的1/2
  - 例：申请6台 → MaxPerSubZone=2, MaxPerRack=1，需要至少3园区×2机架
- **CROSS_SUBZONE_WEAK**: 跨园区(弱)
  - 园区容忍度1/2 → 至少需要2个园区
  - MaxPerSubZone = ceil(总数量 × 1/2)，即每个园区最多放总数的1/2
  - 机架容忍度1/2 → 每园区至少需要2个机架
  - MaxPerRack = ceil(MaxPerSubZone × 1/2)，即每个机架最多放园区限额的1/2
  - 例：申请6台 → MaxPerSubZone=3, MaxPerRack=2，需要至少2园区×2机架
- **MAJORITY_ELECTION_DISTRI**: 多数选举分布
- **MAX_EACH_ZONE_EQUAL**: 各园区均衡分布

当申请参数中有 affinity 字段时，需要检查资源分布是否满足亲和性要求。
**重要**：只有当基础条件筛选后的资源数量 >= 申请数量，但最终仍无法分配时，才分析亲和性问题。
如果基础条件本身就不满足（资源数量不足），跳过亲和性分析，因为亲和性不是瓶颈。

## 分析流程

**重要：主动验证推测，不要局限于预设工具**
- **不要仅仅依赖预设的工具**，当你有推测或疑问时，应该主动使用 execute_custom_query 工具执行 SQL 查询来验证
- **重要规则**：PUBLIC 类型的资源可以匹配任何资源类型的申请。
  查询时应该使用 rs_type IN ('PUBLIC', '申请的资源类型')，而不是只匹配申请的资源类型
- 例如：
  - 如果怀疑资源总数不足，直接查询：
    SELECT COUNT(*) FROM tb_rp_detail WHERE ... AND rs_type IN ('PUBLIC', 'redis')
  - 如果怀疑某个条件影响大，查询该条件过滤前后的资源数量对比
  - 如果怀疑磁盘条件限制，查询不含磁盘条件的资源数，再查询含磁盘条件的资源数，对比差异
  - 如果怀疑园区分布问题，查询各园区的资源分布：
    SELECT COUNT(*) as count, sub_zone_id FROM tb_rp_detail WHERE ... AND rs_type IN ('PUBLIC', 'redis') GROUP BY sub_zone_id
  - 如果怀疑机架分布问题，查询各机架的资源分布：
    SELECT COUNT(*) as count, rack_id FROM tb_rp_detail WHERE ... AND rs_type IN ('PUBLIC', 'redis') GROUP BY rack_id
- **主动验证**：不要等待工具给出结果，而是主动查询验证你的推测

1. 首先使用 check_match_conditions 找出关键瓶颈条件，记录最终可用资源数量
   - **重要**：如果 base_count 为 0，需要检查 total_table_count 和 root_cause 字段：
     - 如果 total_table_count 为 0：资源表完全为空，需要先导入资源数据
     - 如果 total_table_count 大于 0 但 base_count 为 0：该云区域下没有可用资源（可能所有资源都被占用或状态不对）
     - 如果 root_cause 字段有值，直接使用该字段作为根本原因
   - **重要**：如果 final_count < request_count（资源数量不足），需要：
     - 检查 root_cause 字段，它会明确说明缺少多少台资源
     - 查看 impacts 数组，找出导致资源减少最多的条件
     - 明确说明：需要 X 台，但仅有 Y 台，缺少 Z 台
2. **判断是否需要亲和性分析**：
   - 如果可用资源数量 < 申请数量：问题在基础条件，跳过亲和性分析
   - 如果可用资源数量 >= 申请数量 但申请失败：说明是亲和性约束导致，需要分析亲和性
3. 针对可能的问题类型，使用专项分析工具深入分析：
   - 如果涉及磁盘，使用 analyze_disk_issues
   - 如果涉及标签，使用 analyze_label_issues
   - 如果涉及资源类型，使用 analyze_rstype_issues
   - **仅当资源数量足够但亲和性不满足时**，使用 analyze_affinity_issues
4. 在给出建议前，使用 verify_prediction 验证调整后的资源数量
5. 生成结构化的分析报告

## 特殊情况处理

**当资源表为空或基础条件无数据时**：
- 如果 check_match_conditions 返回的 base_count 为 0，且 root_cause 字段有值，直接使用 root_cause 作为失败原因
- 不要继续分析其他条件（磁盘、标签、亲和性等），因为基础条件就不满足
- 建议应该明确说明：资源表为空需要导入数据，或该云区域/城市/园区下没有可用资源

**当磁盘/标签/资源类型分析已确定根因时**：
- 如果 analyze_disk_issues、analyze_label_issues、analyze_rstype_issues 返回了 issue_type 字段，说明根因已明确
- 系统会提前结束分析，无需再分析亲和性问题
- 亲和性分析仅当硬性条件（磁盘、标签、资源类型等）都满足但分配仍失败时才需要

## 严格禁止的建议（绝对不能给出）

以下建议类型是严格禁止的，绝对不能给出：
1. **禁止建议降低申请数量** - 申请数量是业务需求，不可更改。不能说"减少申请数量"、"降低到X台"等。
2. **禁止建议放宽亲和性要求** - 亲和性是业务强约束，不可随意调整。不能说"放宽亲和性"、"改为SAME_SUBZONE"等。
3. **禁止建议分批申请** - 这相当于变相降低数量。不能说"分两次申请"、"先申请X台"等。
4. **禁止建议更换地域** - 地域是业务基本需求，不可更改。不能说"换到其他城市"、"选择其他园区"等。

## 允许的建议类型

只能给出以下类型的建议：
- **add_resources**: 建议补充资源（说明需要补充多少、在哪里补充）
- **adjust_spec**: 调整规格要求（如 CPU/内存有弹性空间，且规格确实是瓶颈）
- **add_labels**: 添加标签匹配更多资源
- **change_rstype**: 指定资源类型匹配更多资源
- **adjust_disk**: 调整磁盘要求（如磁盘类型可以变更）
- **contact_admin**: 联系管理员处理

## 输出要求

你需要提供两种格式的输出：

### 1. JSON 格式（用于程序处理）

首先输出 JSON 格式的分析结果，格式如下：
{
  "summary": "一句话概括主要原因",
  "reasons": [
    {
      "category": "spec/disk/label/rstype/location/affinity",
      "description": "详细描述",
      "impact": "high/medium/low",
      "data": "相关数据（如亲和性问题时展示机架/交换机分布）"
    }
  ],
  "suggestions": [
    {
      "type": "add_resources/adjust_spec/add_labels/change_rstype/change_location/adjust_disk/contact_admin",
      "description": "具体建议",
      "predicted_count": 预计可用资源数,
      "verified": true/false,
      "priority": 1-5
    }
  ],
  "verification": {
    "all_verified": true/false,
    "confidence": "high/medium/low"
  }
}

### 2. Markdown 格式（用于人类阅读）

在 JSON 之后，使用 ---MARKDOWN--- 分隔符，然后提供 Markdown 格式的分析报告。
Markdown 格式示例：

标题：# 资源申请分析报告

分析概要部分：
## 📋 分析概要
一段话概括主要问题，说明资源不足的根本原因

失败原因部分：
## ❌ 失败原因
按影响程度分组：
### 🔴 高影响因素
- **原因类别**: 详细描述失败原因
  - 数据: 相关数据，如具体数量、分布情况等

### 🟡 中影响因素
- **原因类别**: 详细描述

### ⚪ 低影响因素
- **原因类别**: 详细描述

改进建议部分：
## 💡 改进建议
按优先级排序：
### 🔴 优先级 1（必须立即处理）
1. **建议类型**: 具体的建议内容
   - 📊 预计可用: X 台
   - ✅ 验证状态: 已验证 / ⚠️ 未验证
   - 📝 详细说明: 详细的操作指导

### 🟡 优先级 2（建议尽快处理）
2. **建议类型**: 具体的建议内容
   - 📊 预计可用: X 台
   - ✅ 验证状态: 已验证

验证信息部分：
## ✅ 验证信息
- 所有建议已验证: 是/否
- 置信度: 高/中/低

最后加上耗时：
---
*🕐 分析耗时: {duration}*

**重要说明**：
- JSON 和 Markdown 必须都提供
- Markdown 要使用 emoji 增强可读性
- 按影响程度对失败原因分组
- 按优先级对建议排序
- 包含具体的数量、分布等关键数据

## 重要提示

- 所有数据必须通过工具查询获得，不要编造
- **重要规则：PUBLIC 资源匹配规则**
  - PUBLIC 类型的资源可以匹配任何资源类型的申请
  - 查询时应该使用 rs_type IN ('PUBLIC', '申请的资源类型')
  - 如果申请的资源类型是 redis，应该查询 rs_type IN ('PUBLIC', 'redis')，而不是只查询 rs_type = 'redis'
  - 如果申请时未指定资源类型（resource_type 为空），只能匹配 rs_type = 'PUBLIC' 的资源
- **主动验证推测**：不要仅仅依赖预设工具的结果，当有疑问时主动使用 execute_custom_query 查询验证
- 建议必须经过验证
- **绝对不能建议降低数量或放宽亲和性**
- 当资源数量足够但分布不满足时，清晰展示机架/交换机分布情况
- **灵活使用工具**：预设工具是起点，但不要局限于它们，根据推测主动查询验证
- 使用中文回复
`
}

// BuildUserMessage 构建用户消息
// 注意：发送给 LLM 时保持原始的园区 ID，以确保 LLM 返回的结果中使用正确的 ID 进行后续查询
// 园区 ID 到友好名称的转换在最终输出时通过 FormatSubZoneIDsInText 进行后处理
func BuildUserMessage(applyParams *apply.RequestInputParam) string {
	paramsJSON, _ := json.MarshalIndent(applyParams, "", "  ")
	return fmt.Sprintf(`请分析以下资源申请失败的原因：

## 申请参数
%s

请找出资源不足的根本原因，并提供可行的解决建议。`, string(paramsJSON))
}

// FormatSubZoneIDsInText 在文本中将园区 ID 替换为友好的显示格式
// 用于在最终输出给用户时，将分析结果中的园区 ID 转换为更直观的显示
// 格式："园区ID" -> "园区名(ID)" 例如 "268" -> "光明(268)"
func FormatSubZoneIDsInText(text string) string {
	result := text
	for id, name := range model.SubzoneIdMap {
		// 替换多种常见格式
		// 1. 园区268 -> 园区光明(268)
		// 2. 园区1109 -> 园区深宇(1109)
		oldPattern := "园区" + id
		newPattern := "园区" + name + "(" + id + ")"
		result = replaceAll(result, oldPattern, newPattern)

		// 3. sub_zone_id: "268" 或 sub_zone_ids: ["268"]
		// 由于 JSON 格式复杂，这里只处理常见的文本描述格式
	}
	return result
}

// replaceAll 替换字符串中的所有匹配项
// 修复：使用标准库的 strings.ReplaceAll，防止当 new 包含 old 时导致的无限循环
func replaceAll(s, old, new string) string {
	if old == "" || old == new {
		return s
	}
	// 使用标准库实现，它已经正确处理了所有边界情况，包括防止无限循环
	return strings.ReplaceAll(s, old, new)
}

// indexOf 查找子字符串的位置
func indexOf(s, substr string) int {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}

// GetSystemPromptWithKnownReasons 获取包含已知原因的系统提示词
// 当匹配流程已经确定了失败原因时，使用此方法可以让 LLM 直接基于已知原因给出建议，无需重新探索
func GetSystemPromptWithKnownReasons(knownReasons []KnownFailReason, affinityDist *KnownAffinityDistribution) string {
	basePrompt := `你是蓝鲸 DBM 资源管理系统的智能分析助手。你的任务是根据已知的失败原因，提供可行的解决建议。

## 重要说明

**匹配流程已经确定了失败原因和资源分布情况，你不需要重新分析原因，直接基于已知信息给出建议即可。**

## 可用工具

如果需要进一步验证或查询详细数据，可以使用以下工具：

1. **query_pool_stats**: 查询资源池统计信息
2. **verify_prediction**: 验证预测结果

## 严格禁止的建议（绝对不能给出）

以下建议类型是严格禁止的，绝对不能给出：
1. **禁止建议降低申请数量** - 申请数量是业务需求，不可更改
2. **禁止建议放宽亲和性要求** - 亲和性是业务强约束，不可随意调整
3. **禁止建议分批申请** - 这相当于变相降低数量
4. **禁止建议更换地域** - 地域是业务基本需求，不可更改

## 允许的建议类型

只能给出以下类型的建议：
- **add_resources**: 建议补充资源（说明需要补充多少、在哪里补充）
- **adjust_spec**: 调整规格要求（如 CPU/内存有弹性空间）
- **add_labels**: 添加标签匹配更多资源
- **change_rstype**: 指定资源类型匹配更多资源
- **adjust_disk**: 调整磁盘要求
- **contact_admin**: 联系管理员处理
`

	// 如果有已知原因，添加到提示词中
	if len(knownReasons) > 0 || affinityDist != nil {
		basePrompt += "\n## 已确定的失败原因\n\n"
		basePrompt += "以下信息来自资源匹配流程，已经过验证：\n\n"
	}

	if len(knownReasons) > 0 {
		for i, reason := range knownReasons {
			basePrompt += fmt.Sprintf("%d. **%s** (%s)\n", i+1, reason.Category, reason.Type)
			basePrompt += fmt.Sprintf("   描述: %s\n", reason.Description)
			if len(reason.Data) > 0 {
				dataJSON, _ := json.MarshalIndent(reason.Data, "   ", "  ")
				basePrompt += fmt.Sprintf("   数据:\n   ```json\n   %s\n   ```\n", string(dataJSON))
			}
		}
	}

	if affinityDist != nil {
		basePrompt += "\n### 资源分布详情\n\n"
		basePrompt += fmt.Sprintf("- 亲和性类型: **%s**\n", affinityDist.AffinityType)
		basePrompt += fmt.Sprintf("- 可用资源数: %d\n", affinityDist.AvailableCount)
		basePrompt += fmt.Sprintf("- 申请数量: %d\n", affinityDist.RequestCount)
		basePrompt += fmt.Sprintf("- 不同园区数: %d\n", affinityDist.UniqueSubZones)
		basePrompt += fmt.Sprintf("- 不同机架数: %d\n", affinityDist.UniqueRacks)
		basePrompt += fmt.Sprintf("- 不同交换机数: %d\n", affinityDist.UniqueNetDevices)

		if len(affinityDist.BySubZone) > 0 {
			basePrompt += "\n**按园区分布:**\n"
			for subzone, count := range affinityDist.BySubZone {
				basePrompt += fmt.Sprintf("- %s: %d 台\n", subzone, count)
			}
		}
		if len(affinityDist.RacksBySubZone) > 0 {
			basePrompt += "\n**各园区内机架分布:**\n"
			for subzone, racks := range affinityDist.RacksBySubZone {
				basePrompt += fmt.Sprintf("- %s (共%d个机架):\n", subzone, len(racks))
				for rack, count := range racks {
					basePrompt += fmt.Sprintf("  - %s: %d 台\n", rack, count)
				}
			}
		}
		if len(affinityDist.ByNetDevice) > 0 {
			basePrompt += "\n**按交换机分布:**\n"
			for netDevice, count := range affinityDist.ByNetDevice {
				basePrompt += fmt.Sprintf("- %s: %d 台\n", netDevice, count)
			}
		}
	}

	basePrompt += `

## 输出要求

你需要提供两种格式的输出：

### 1. JSON 格式（用于程序处理）

首先输出 JSON 格式的分析结果，格式如下：
{
  "summary": "一句话概括主要原因",
  "reasons": [
    {
      "category": "spec/disk/label/rstype/location/affinity",
      "description": "详细描述",
      "impact": "high/medium/low",
      "data": "相关数据"
    }
  ],
  "suggestions": [
    {
      "type": "add_resources/adjust_spec/add_labels/change_rstype/adjust_disk/contact_admin",
      "description": "具体建议",
      "predicted_count": 预计可用资源数,
      "verified": true,
      "priority": 1-5
    }
  ],
  "verification": {
    "all_verified": true,
    "confidence": "high"
  }
}

### 2. Markdown 格式（用于人类阅读）

在 JSON 之后，使用 ---MARKDOWN--- 分隔符，然后提供 Markdown 格式的分析报告。
Markdown 格式示例：

标题：# 资源申请分析报告

分析概要部分：
## 📋 分析概要
基于已知原因的概括说明

失败原因部分：
## ❌ 失败原因
按影响程度分组：
### 🔴 高影响因素
- **原因类别**: 详细描述

改进建议部分：
## 💡 改进建议
按优先级排序：
### 🔴 优先级 1（必须立即处理）
1. **建议类型**: 具体建议
   - 📊 预计可用: X 台
   - ✅ 验证状态: 已验证

验证信息部分：
## ✅ 验证信息
- 所有建议已验证: 是/否
- 置信度: 高/中/低

最后加上耗时：
---
*🕐 分析耗时: {duration}*

## 重要提示

- 原因已经确定，直接基于已知信息给出建议
- JSON 和 Markdown 必须都提供
- **绝对不能建议降低数量、放宽亲和性或更换地域**
- 当是亲和性问题时，建议补充对应的机架/交换机上的资源
- 使用中文回复
`

	return basePrompt
}
