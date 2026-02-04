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
	"fmt"
	"sort"
	"strings"
)

// FormatAnalysisResultToMarkdown 将分析结果格式化为 Markdown 文本
// 当 LLM 没有返回 Markdown 格式时，使用此函数从 JSON 数据生成 Markdown
func FormatAnalysisResultToMarkdown(result *AnalysisResult) string {
	var builder strings.Builder

	// 标题
	builder.WriteString("# 资源申请分析报告\n\n")

	// 分析概要
	builder.WriteString("## 📋 分析概要\n\n")
	if result.Summary != "" {
		builder.WriteString(result.Summary)
		builder.WriteString("\n\n")
	} else {
		builder.WriteString("资源申请失败，请查看下方详细分析。\n\n")
	}

	// 失败原因
	if len(result.Reasons) > 0 {
		builder.WriteString("## ❌ 失败原因\n\n")

		// 按影响程度分组
		highImpact := []FailureReason{}
		mediumImpact := []FailureReason{}
		lowImpact := []FailureReason{}

		for _, reason := range result.Reasons {
			switch reason.Impact {
			case "high":
				highImpact = append(highImpact, reason)
			case "medium":
				mediumImpact = append(mediumImpact, reason)
			case "low":
				lowImpact = append(lowImpact, reason)
			default:
				mediumImpact = append(mediumImpact, reason)
			}
		}

		// 高影响因素
		if len(highImpact) > 0 {
			builder.WriteString("### 🔴 高影响因素\n\n")
			for _, reason := range highImpact {
				builder.WriteString(fmt.Sprintf("- **%s**: %s\n", getCategoryName(reason.Category), reason.Description))
				if reason.Data != nil {
					builder.WriteString(fmt.Sprintf("  - 数据: %v\n", reason.Data))
				}
			}
			builder.WriteString("\n")
		}

		// 中影响因素
		if len(mediumImpact) > 0 {
			builder.WriteString("### 🟡 中影响因素\n\n")
			for _, reason := range mediumImpact {
				builder.WriteString(fmt.Sprintf("- **%s**: %s\n", getCategoryName(reason.Category), reason.Description))
				if reason.Data != nil {
					builder.WriteString(fmt.Sprintf("  - 数据: %v\n", reason.Data))
				}
			}
			builder.WriteString("\n")
		}

		// 低影响因素
		if len(lowImpact) > 0 {
			builder.WriteString("### ⚪ 低影响因素\n\n")
			for _, reason := range lowImpact {
				builder.WriteString(fmt.Sprintf("- **%s**: %s\n", getCategoryName(reason.Category), reason.Description))
				if reason.Data != nil {
					builder.WriteString(fmt.Sprintf("  - 数据: %v\n", reason.Data))
				}
			}
			builder.WriteString("\n")
		}
	}

	// 改进建议
	if len(result.Suggestions) > 0 {
		builder.WriteString("## 💡 改进建议\n\n")

		// 按优先级排序
		sortedSuggestions := make([]Suggestion, len(result.Suggestions))
		copy(sortedSuggestions, result.Suggestions)
		sort.Slice(sortedSuggestions, func(i, j int) bool {
			return sortedSuggestions[i].Priority < sortedSuggestions[j].Priority
		})

		// 按优先级分组
		currentPriority := -1
		suggestionIndex := 1

		for _, suggestion := range sortedSuggestions {
			if suggestion.Priority != currentPriority {
				currentPriority = suggestion.Priority
				priorityLabel := getPriorityLabel(currentPriority)
				builder.WriteString(fmt.Sprintf("\n### %s\n\n", priorityLabel))
				suggestionIndex = 1
			}

			builder.WriteString(fmt.Sprintf("%d. **%s**: %s\n", suggestionIndex, getSuggestionTypeName(suggestion.Type), suggestion.Description))

			if suggestion.PredictedCount > 0 {
				builder.WriteString(fmt.Sprintf("   - 📊 预计可用: %d 台\n", suggestion.PredictedCount))
			}

			if suggestion.Verified {
				builder.WriteString("   - ✅ 验证状态: 已验证\n")
			} else {
				builder.WriteString("   - ⚠️ 验证状态: 未验证\n")
			}

			builder.WriteString("\n")
			suggestionIndex++
		}
	}

	// 验证信息
	if result.Verification != nil {
		builder.WriteString("## ✅ 验证信息\n\n")
		if result.Verification.AllVerified {
			builder.WriteString("- 所有建议已验证: 是\n")
		} else {
			builder.WriteString("- 所有建议已验证: 否\n")
		}

		confidenceLabel := getConfidenceLabel(result.Verification.Confidence)
		builder.WriteString(fmt.Sprintf("- 置信度: %s\n", confidenceLabel))
		builder.WriteString("\n")
	}

	// 分析耗时
	if result.Duration != "" {
		builder.WriteString("---\n")
		builder.WriteString(fmt.Sprintf("*🕐 分析耗时: %s*\n", result.Duration))
	}

	return builder.String()
}

// getCategoryName 获取分类的中文名称
func getCategoryName(category string) string {
	categoryNames := map[string]string{
		"spec":     "规格不匹配",
		"disk":     "磁盘条件",
		"label":    "标签匹配",
		"rstype":   "资源类型",
		"location": "位置分布",
		"affinity": "亲和性约束",
	}

	if name, ok := categoryNames[category]; ok {
		return name
	}
	return category
}

// getSuggestionTypeName 获取建议类型的中文名称
func getSuggestionTypeName(suggestionType string) string {
	typeNames := map[string]string{
		"add_resources":   "补充资源",
		"adjust_spec":     "调整规格",
		"add_labels":      "添加标签",
		"change_rstype":   "指定资源类型",
		"adjust_disk":     "调整磁盘要求",
		"contact_admin":   "联系管理员",
		"change_location": "调整位置",
	}

	if name, ok := typeNames[suggestionType]; ok {
		return name
	}
	return suggestionType
}

// getPriorityLabel 获取优先级标签
func getPriorityLabel(priority int) string {
	switch priority {
	case 1:
		return "🔴 优先级 1（必须立即处理）"
	case 2:
		return "🟡 优先级 2（建议尽快处理）"
	case 3:
		return "🟢 优先级 3（可以稍后处理）"
	case 4:
		return "🔵 优先级 4（建议考虑）"
	case 5:
		return "⚪ 优先级 5（可选）"
	default:
		return fmt.Sprintf("优先级 %d", priority)
	}
}

// getConfidenceLabel 获取置信度标签
func getConfidenceLabel(confidence string) string {
	confidenceLabels := map[string]string{
		"high":   "高",
		"medium": "中",
		"low":    "低",
	}

	if label, ok := confidenceLabels[confidence]; ok {
		return label
	}
	return confidence
}
