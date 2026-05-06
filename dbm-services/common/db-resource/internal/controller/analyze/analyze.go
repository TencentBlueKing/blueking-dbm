/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package analyze 资源分析 API
package analyze

import (
	"context"

	"dbm-services/common/db-resource/internal/controller"
	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/agent"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// AnalyzeHandler 分析处理器
type AnalyzeHandler struct {
	controller.BaseHandler
}

// RegisterRouter 注册路由
func (c *AnalyzeHandler) RegisterRouter(engine *gin.Engine) {
	r := engine.Group("resource")
	{
		r.POST("/analyze", c.AnalyzeResource)
		r.POST("/quick-analyze", c.QuickAnalyzeResource)
		r.POST("/analysis/result", c.GetAnalysisResult)
	}
}

// AnalyzeResourceParam 分析资源参数
type AnalyzeResourceParam struct {
	ApplyParams *apply.RequestInputParam `json:"apply_params"`
}

// AnalyzeResource 使用 LLM 分析资源匹配问题
func (c *AnalyzeHandler) AnalyzeResource(r *gin.Context) {
	var param AnalyzeResourceParam
	if c.Prepare(r, &param) != nil {
		return
	}

	if param.ApplyParams == nil {
		c.SendResponse(r, nil, map[string]interface{}{
			"error": "apply_params is required",
		})
		return
	}

	// 检查 LLM 分析器是否可用
	analyzer := agent.GetAnalyzer()
	if analyzer == nil || !analyzer.IsEnabled() {
		c.SendResponse(r, nil, map[string]interface{}{
			"error":   "LLM analyzer is not enabled",
			"message": "请在配置文件中启用 LLM 分析功能",
		})
		return
	}

	// 执行分析
	ctx, cancel := context.WithTimeout(r.Request.Context(), agent.LLMAnalysisTimeout)
	defer cancel()

	result, err := analyzer.Analyze(ctx, param.ApplyParams)
	if err != nil {
		logger.Error("LLM analyze failed: %v", err)
		c.SendResponse(r, nil, map[string]interface{}{
			"error":   "analyze failed",
			"message": err.Error(),
		})
		return
	}

	c.SendResponse(r, nil, result)
}

// QuickAnalyzeParam 快速分析参数
type QuickAnalyzeParam struct {
	BkCloudID      int      `json:"bk_cloud_id" binding:"required"`
	City           string   `json:"city"`
	CpuMin         int      `json:"cpu_min"`
	CpuMax         int      `json:"cpu_max"`
	MemMin         int      `json:"mem_min"`
	MemMax         int      `json:"mem_max"`
	DiskMountPoint string   `json:"disk_mount_point"`
	DiskMinSize    int      `json:"disk_min_size"`
	DiskType       string   `json:"disk_type"`
	ResourceType   string   `json:"resource_type"`
	Labels         []string `json:"labels"`
	RequestCount   int      `json:"request_count" binding:"required,min=1"`
}

// QuickAnalyzeResource 快速分析资源（不使用 LLM）
func (c *AnalyzeHandler) QuickAnalyzeResource(r *gin.Context) {
	var param QuickAnalyzeParam
	if c.Prepare(r, &param) != nil {
		return
	}

	// 创建快速分析器
	quickAnalyzer := agent.NewQuickAnalysis(model.DB.Self)

	// 构建分析参数
	analysisParams := map[string]interface{}{
		"bk_cloud_id":      float64(param.BkCloudID),
		"city":             param.City,
		"cpu_min":          float64(param.CpuMin),
		"cpu_max":          float64(param.CpuMax),
		"mem_min":          float64(param.MemMin),
		"mem_max":          float64(param.MemMax),
		"disk_mount_point": param.DiskMountPoint,
		"disk_min_size":    float64(param.DiskMinSize),
		"disk_type":        param.DiskType,
		"resource_type":    param.ResourceType,
		"request_count":    float64(param.RequestCount),
	}

	if len(param.Labels) > 0 {
		labels := make([]interface{}, len(param.Labels))
		for i, l := range param.Labels {
			labels[i] = l
		}
		analysisParams["labels"] = labels
	}

	// 执行快速分析
	result, err := quickAnalyzer.Analyze(analysisParams)
	if err != nil {
		logger.Error("Quick analyze failed: %v", err)
		c.SendResponse(r, nil, map[string]interface{}{
			"error":   "analyze failed",
			"message": err.Error(),
		})
		return
	}

	c.SendResponse(r, nil, result)
}

// GetAnalysisResultParam 查询参数
type GetAnalysisResultParam struct {
	BillId int `json:"bill_id" form:"bill_id" binding:"required"`
}

// GetAnalysisResult 根据单据ID查询智能体分析结果
// GET /resource/analysis/result?bill_id=xxx
func (c *AnalyzeHandler) GetAnalysisResult(r *gin.Context) {
	var param GetAnalysisResultParam
	if err := r.ShouldBindJSON(&param); err != nil {
		c.SendResponse(r, err, nil)
		return
	}

	var record model.TbRpAnalysisResult
	err := model.DB.Self.Where("bill_id = ?", param.BillId).First(&record).Error
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			// 未找到记录，返回提示文本
			c.SendResponse(r, nil, map[string]interface{}{
				"markdown_text": "# 分析结果\n\n未找到该单据的分析记录。",
			})
			return
		}
		c.SendResponse(r, err, nil)
		return
	}

	var markdownText string

	// 根据状态返回不同的文本
	switch record.Status {
	case model.AnalysisStatusPending:
		markdownText = "# 资源申请分析\n\n⏳ **分析待处理**\n\n您的资源申请分析任务已提交，正在等待处理，请稍候...\n\n---\n*刷新页面查看最新状态*"

	case model.AnalysisStatusRunning:
		markdownText = "# 资源申请分析\n\n🔄 **分析进行中**\n\n正在智能分析您的资源申请，这可能需要几十秒时间，请耐心等待...\n\n---\n*刷新页面查看最新状态*"

	case model.AnalysisStatusCompleted:
		// 返回实际的分析结果
		if record.MarkdownText != "" {
			markdownText = record.MarkdownText
		} else {
			markdownText = "# 资源申请分析报告\n\n分析已完成，但未生成报告内容。"
		}

	case model.AnalysisStatusFailed:
		// 返回失败信息
		errorMsg := record.ErrorMsg
		if errorMsg == "" {
			errorMsg = "未知错误"
		}
		markdownText = "# 资源申请分析\n\n❌ **分析失败**\n\n分析过程中发生错误：\n\n```\n" + errorMsg + "\n```\n\n---\n*请检查申请参数或联系管理员*"

	default:
		markdownText = "# 资源申请分析\n\n⚠️ **未知状态**\n\n当前分析状态: " + record.Status
	}

	c.SendResponse(r, nil, map[string]interface{}{
		"markdown_text": markdownText,
	})
}
