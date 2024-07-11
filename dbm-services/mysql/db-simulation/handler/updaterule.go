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
	"dbm-services/mysql/db-simulation/model"
)

// UpdateRuleParam TODO
type UpdateRuleParam struct {
	Item interface{} `json:"item" binding:"required"`
	ID   int         `json:"id" binding:"required"`
}

// UpdateRule TODO
func UpdateRule(r *gin.Context) {
	logger.Info("UpdateRule...")
	var param UpdateRuleParam
	// 将request中的数据按照json格式直接解析到结构体中
	if err := r.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(r, err, nil, "")
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
				errReturn(r, &tsr)
				return
			}
			updateTable(param.ID, int(v))
		} else {
			err = errors.New("not int")
			logger.Error("Type of error: %s", err)
			SendResponse(r, err, nil, "")
			return
		}
	case bool:
		if tsr.ItemType == "bool" {
			updateTable(param.ID, fmt.Sprintf("%t", v))
		} else {
			errReturn(r, &tsr)
			return
		}
	case string:
		if tsr.ItemType == "string" {
			updateTable(param.ID, fmt.Sprintf("%+q", v))
		} else {
			errReturn(r, &tsr)
			return
		}
	case []interface{}:
		if tsr.ItemType == "arry" {
			updateTable(param.ID, fmt.Sprintf("%+q", v))
		} else {
			errReturn(r, &tsr)
			return
		}
	default:
		err = errors.New("illegal type")
		logger.Error("%s", err)
		SendResponse(r, err, nil, "")
		return
	}
	SendResponse(r, nil, "sucessed", "")
}

func updateTable(id int, item interface{}) {
	model.DB.Model(&model.TbSyntaxRule{}).Where("id", id).Update("item", item)
}

func errReturn(r *gin.Context, tsr *model.TbSyntaxRule) {
	err := fmt.Errorf("%s type required", tsr.ItemType)
	logger.Error("Item type error: %s", err)
	SendResponse(r, err, nil, "")
}
