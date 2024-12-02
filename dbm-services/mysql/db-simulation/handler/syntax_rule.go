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
	var tsr model.TbSyntaxRule
	model.DB.Select("item_type").First(&tsr, param.ID)

	var err error
	switch v := param.Item.(type) {
	case float64:
		// 判断float64存的是整数
		if v == float64(int64(v)) {
			if !(tsr.ItemType == "int") {
				m.errReturn(r, &tsr)
				return
			}
			updateTable(param.ID, int(v))
		} else {
			err = errors.New("not int")
			logger.Error("Type of error: %s", err)
			m.SendResponse(r, err, nil)
			return
		}
	case bool:
		if tsr.ItemType == "bool" {
			updateTable(param.ID, fmt.Sprintf("%t", v))
		} else {
			m.errReturn(r, &tsr)
			return
		}
	case string:
		if tsr.ItemType == "string" {
			updateTable(param.ID, fmt.Sprintf("%+q", v))
		} else {
			m.errReturn(r, &tsr)
			return
		}
	case []interface{}:
		if tsr.ItemType == "arry" {
			updateTable(param.ID, fmt.Sprintf("%+q", v))
		} else {
			m.errReturn(r, &tsr)
			return
		}
	default:
		err = errors.New("illegal type")
		logger.Error("%s", err)
		m.SendResponse(r, err, nil)
		return
	}
	m.SendResponse(r, nil, "sucessed")
}

func updateTable(id int, item interface{}) {
	model.DB.Model(&model.TbSyntaxRule{}).Where("id", id).Update("item", item)
}

func (m *ManageRuleHandler) errReturn(r *gin.Context, tsr *model.TbSyntaxRule) {
	err := fmt.Errorf("%s type required", tsr.ItemType)
	logger.Error("Item type error: %s", err)
	m.SendResponse(r, err, nil)
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
