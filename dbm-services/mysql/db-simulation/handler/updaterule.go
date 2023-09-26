package handler

import (
	"errors"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/model"

	"github.com/gin-gonic/gin"
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
			if tsr.ItemType == "int" {
				updateTable(param.ID, int(v))
			} else {
				errReturn(r, &tsr)
				return
			}
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
