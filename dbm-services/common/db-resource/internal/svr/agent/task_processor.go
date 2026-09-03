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
	"runtime/debug"
	"time"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/db-resource/internal/svr/apply"
	"dbm-services/common/db-resource/internal/svr/task"
	"dbm-services/common/go-pubpkg/logger"

	"gorm.io/gorm"
)

// parseFailureEvidence 解析申请失败现场，解析失败不阻断分析
func parseFailureEvidence(billID string, raw json.RawMessage) *apply.ApplyFailureEvidence {
	if len(raw) == 0 {
		return nil
	}
	var evidence apply.ApplyFailureEvidence
	if err := json.Unmarshal(raw, &evidence); err != nil {
		logger.Warn("Failed to unmarshal failure evidence for bill %s: %v", billID, err)
		return nil
	}
	return &evidence
}

// markAnalysisFailed 将分析记录标为失败。billID 为空或 DB 未就绪时直接返回。
func markAnalysisFailed(billID, errorMsg, duration string) {
	if billID == "" || model.DB == nil || model.DB.Self == nil {
		return
	}
	update := map[string]interface{}{
		"status":      model.AnalysisStatusFailed,
		"error_msg":   errorMsg,
		"update_time": time.Now(),
	}
	if duration != "" {
		update["duration"] = duration
	}
	if err := model.DB.Self.Model(&model.TbRpAnalysisResult{}).
		Where("bill_id = ?", billID).
		Updates(update).Error; err != nil {
		logger.Error("Failed to mark analysis failed for bill %s: %v", billID, err)
	}
}

// ProcessAnalysisTask 处理智能体分析任务
func ProcessAnalysisTask(item task.AnalysisTaskItem) {
	billID := item.BillID
	startTime := time.Now()
	defer func() {
		if r := recover(); r != nil {
			logger.Error("Analysis task panic: %v, stack: %s", r, string(debug.Stack()))
			markAnalysisFailed(billID, fmt.Sprintf("analysis panic: %v", r), time.Since(startTime).String())
		}
	}()

	applyParamsJSON := item.ApplyParams
	if billID == "" || applyParamsJSON == nil {
		logger.Error("Invalid billID or applyParamsJSON, skip analysis")
		return
	}

	// 申请失败现场，可为空（同步分析入口不带现场）
	evidence := parseFailureEvidence(billID, item.Evidence)
	// 1. 检查单据ID是否存在，存在则覆盖，不存在则创建
	var existingRecord model.TbRpAnalysisResult
	err := model.DB.Self.Where("bill_id = ?", billID).First(&existingRecord).Error

	if err == nil {
		// 单据ID已存在，覆盖现有记录
		updateData := map[string]interface{}{
			"apply_params": applyParamsJSON,
			"status":       model.AnalysisStatusPending,
			"error_msg":    "", // 清除之前的错误信息
			"duration":     "", // 清除之前的耗时
			"update_time":  time.Now(),
		}
		// 如果之前有分析结果，也清除掉
		if existingRecord.AnalysisResult != nil {
			updateData["analysis_result"] = nil
		}

		if err := model.DB.Self.Model(&model.TbRpAnalysisResult{}).
			Where("bill_id = ?", billID).
			Updates(updateData).Error; err != nil {
			logger.Error("Failed to update analysis record for bill %s: %v", billID, err)
			return
		}
		logger.Info("Analysis record for bill %s already exists, overwriting", billID)
	} else if err == gorm.ErrRecordNotFound {
		// 单据ID不存在，创建新记录
		record := model.TbRpAnalysisResult{
			BillId:      billID,
			ApplyParams: applyParamsJSON,
			Status:      model.AnalysisStatusPending,
			CreateTime:  time.Now(),
			UpdateTime:  time.Now(),
		}

		if err := model.DB.Self.Create(&record).Error; err != nil {
			logger.Error("Failed to create analysis record for bill %s: %v", billID, err)
			return
		}
		logger.Info("Created new analysis record for bill %s", billID)
	} else {
		// 其他数据库错误
		logger.Error("Failed to query analysis record for bill %s: %v", billID, err)
		return
	}

	// 2. 更新状态为 running
	if err := model.DB.Self.Model(&model.TbRpAnalysisResult{}).
		Where("bill_id = ?", billID).
		Update("status", model.AnalysisStatusRunning).Error; err != nil {
		logger.Error("Failed to update status to running for bill %s: %v", billID, err)
	}

	// 3. 调用智能体分析
	ctx, cancel := context.WithTimeout(context.Background(), LLMAnalysisTimeout)
	defer cancel()

	analyzer := GetAnalyzer()
	if analyzer == nil || !analyzer.IsEnabled() {
		logger.Warn("LLM analyzer is not enabled, skip analysis for bill %s", billID)
		markAnalysisFailed(billID, "LLM analyzer is not enabled", "")
		return
	}

	// 解析申请参数
	var applyParams apply.RequestInputParam
	if err := json.Unmarshal(applyParamsJSON, &applyParams); err != nil {
		logger.Error("Failed to unmarshal apply params for bill %s: %v", billID, err)
		markAnalysisFailed(billID, fmt.Sprintf("Failed to unmarshal params: %v", err), "")
		return
	}

	result, err := analyzer.AnalyzeWithScene(ctx, &applyParams, evidence)
	duration := time.Since(startTime).String()

	// 4. 更新分析结果
	if err != nil {
		logger.Error("Analysis failed for bill %s: %v", billID, err)
		markAnalysisFailed(billID, err.Error(), duration)
		return
	}

	resultJSON, err := json.Marshal(result)
	if err != nil {
		logger.Error("Failed to marshal analysis result for bill %s: %v", billID, err)
		markAnalysisFailed(billID, fmt.Sprintf("Failed to marshal result: %v", err), duration)
		return
	}

	// 成功完成
	if err := model.DB.Self.Model(&model.TbRpAnalysisResult{}).
		Where("bill_id = ?", billID).
		Updates(map[string]interface{}{
			"status":          model.AnalysisStatusCompleted,
			"analysis_result": resultJSON,
			"markdown_text":   result.MarkdownText,
			"duration":        duration,
		}).Error; err != nil {
		logger.Error("Failed to update analysis result for bill %s: %v", billID, err)
	} else {
		logger.Info("Analysis completed for bill %s, duration: %s", billID, duration)
	}
}
