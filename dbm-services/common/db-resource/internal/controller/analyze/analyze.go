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
	"encoding/json"
	"time"

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
		r.GET("/analysis/result", c.GetAnalysisResult)
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
	ctx, cancel := context.WithTimeout(r.Request.Context(), 60*time.Second)
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
	BillId string `json:"bill_id" form:"bill_id" binding:"required"`
}

// GetAnalysisResult 根据单据ID查询智能体分析结果
// GET /resource/analysis/result?bill_id=xxx
func (c *AnalyzeHandler) GetAnalysisResult(r *gin.Context) {
	var param GetAnalysisResultParam
	if err := r.ShouldBindQuery(&param); err != nil {
		c.SendResponse(r, err, nil)
		return
	}

	var record model.TbRpAnalysisResult
	err := model.DB.Self.Where("bill_id = ?", param.BillId).First(&record).Error
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			// 未找到记录，返回空对象
			c.SendResponse(r, nil, map[string]interface{}{})
			return
		}
		c.SendResponse(r, err, nil)
		return
	}

	// 如果状态是 pending 或 running，返回空对象（分析未完成）
	if record.Status == model.AnalysisStatusPending ||
		record.Status == model.AnalysisStatusRunning {
		c.SendResponse(r, nil, map[string]interface{}{})
		return
	}

	// 如果状态是 completed，返回分析结果
	if record.Status == model.AnalysisStatusCompleted {
		var result map[string]interface{}
		if len(record.AnalysisResult) > 0 {
			if err := json.Unmarshal(record.AnalysisResult, &result); err != nil {
				logger.Error("Failed to unmarshal analysis result: %v", err)
				c.SendResponse(r, nil, map[string]interface{}{})
				return
			}
		} else {
			result = map[string]interface{}{}
		}
		c.SendResponse(r, nil, result)
		return
	}

	// 如果状态是 failed，返回空对象
	if record.Status == model.AnalysisStatusFailed {
		c.SendResponse(r, nil, map[string]interface{}{})
		return
	}

	// 默认返回空对象
	c.SendResponse(r, nil, map[string]interface{}{})
}
