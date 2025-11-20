/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package handler

import (
	"encoding/json"
	"errors"
	"fmt"

	"github.com/gin-gonic/gin"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/syntax"
	"dbm-services/mysql/db-simulation/model"
)

// ManageRuleHandler manage rule handler
type ManageRuleHandler struct {
	BaseHandler
}

// RegisterRouter 注册路由信息
func (m *ManageRuleHandler) RegisterRouter(engine *gin.Engine) {
	r := engine.Group("/rule")
	{
		r.POST("/manage", m.ManageRule)
		r.GET("/getall", m.GetAllRule)
		r.POST("/update", m.UpdateRule)
		r.POST("/reload", m.ReloadRule)
	}
}

// OptRuleParam 语法规则管理参数
type OptRuleParam struct {
	RuleID int  `json:"rule_id" binding:"required"`
	Status bool `json:"status" `
}

// ManageRule 语法规则管理
func (m *ManageRuleHandler) ManageRule(c *gin.Context) {
	var param OptRuleParam
	if err := m.Prepare(c, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}
	result := model.DB.Model(&model.TbSyntaxRule{}).Where(&model.TbSyntaxRule{ID: param.RuleID}).Update("status",
		param.Status).Limit(1)
	if result.Error != nil {
		logger.Error("update rule status failed %s,affect rows %d", result.Error.Error(), result.RowsAffected)
		m.SendResponse(c, result.Error, result.Error)
		return
	}
	m.SendResponse(c, nil, "ok")
}

// GetAllRule 获取所有权限规则
func (m *ManageRuleHandler) GetAllRule(c *gin.Context) {
	var rs []model.TbSyntaxRule
	if err := model.DB.Find(&rs).Error; err != nil {
		logger.Error("query rules failed %s", err.Error())
		m.SendResponse(c, err, err.Error())
		return
	}
	m.SendResponse(c, nil, rs)
}

// UpdateRuleParam 更新语法规则参数
type UpdateRuleParam struct {
	Item interface{} `json:"item" binding:"required"`
	ID   int         `json:"id" binding:"required"`
}

// UpdateRule update syntax rule
func (m *ManageRuleHandler) UpdateRule(r *gin.Context) {
	logger.Info("UpdateRule...")
	var param UpdateRuleParam
	// 将request中的数据按照json格式直接解析到结构体中
	if err := m.Prepare(r, &param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		return
	}

	// 查询规则的类型信息
	var tsr model.TbSyntaxRule
	if err := model.DB.Select("item_type").First(&tsr, param.ID).Error; err != nil {
		logger.Error("query rule failed: %s", err)
		m.SendResponse(r, err, nil)
		return
	}

	// 验证并转换值
	value, err := m.validateAndConvertValue(param.Item, tsr.ItemType)
	if err != nil {
		logger.Error("validate value failed: %s", err)
		m.SendResponse(r, err, nil)
		return
	}

	// 更新数据库
	if err := updateTableWithError(param.ID, value); err != nil {
		logger.Error("update rule failed: %s", err)
		m.SendResponse(r, err, nil)
		return
	}

	m.SendResponse(r, nil, "succeeded")
}

// validateAndConvertValue 验证并转换参数值为合适的存储格式
func (m *ManageRuleHandler) validateAndConvertValue(item interface{}, expectedType string) (interface{}, error) {
	switch v := item.(type) {
	case float64:
		// JSON 数字默认解析为 float64，需要判断是否为整数
		if v != float64(int64(v)) {
			return nil, errors.New("value is not an integer")
		}
		if expectedType != model.IntItem {
			return nil, fmt.Errorf("%s type required, but got number", expectedType)
		}
		return int(v), nil

	case bool:
		if expectedType != model.BoolItem {
			return nil, fmt.Errorf("%s type required, but got boolean", expectedType)
		}
		return v, nil

	case string:
		if expectedType != model.StringItem {
			return nil, fmt.Errorf("%s type required, but got string", expectedType)
		}
		return v, nil

	case []interface{}:
		if expectedType != model.ArryItem {
			return nil, fmt.Errorf("%s type required, but got array", expectedType)
		}
		// 将数组序列化为 JSON 字符串存储
		jsonBytes, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("serialize array failed: %w", err)
		}
		return string(jsonBytes), nil

	default:
		return nil, fmt.Errorf("unsupported type: %T", item)
	}
}

// updateTableWithError 更新规则表并返回错误
func updateTableWithError(id int, item interface{}) error {
	result := model.DB.Model(&model.TbSyntaxRule{}).Where("id", id).Update("item", item)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errors.New("no rows affected, rule may not exist")
	}
	return nil
}

// ReloadRule  trigger reload rule
func (m *ManageRuleHandler) ReloadRule(c *gin.Context) {
	err := syntax.ReloadRuleFromDb()
	if err != nil {
		logger.Error("reload rule from db failed %s", err.Error())
		m.SendResponse(c, err, nil)
		return
	}
	m.SendResponse(c, nil, "ok")
}
