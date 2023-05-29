package handler

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/model"

	"github.com/gin-gonic/gin"
)

// OptRuleParam TODO
type OptRuleParam struct {
	RuleId int  `json:"rule_id" binding:"required"`
	Status bool `json:"status" `
	// GroupName string `json:"group_name"`
	// RuleName  string `json:"rule_name"`
}

// ManageRule TODO
func ManageRule(c *gin.Context) {
	var param OptRuleParam
	if err := c.ShouldBindJSON(&param); err != nil {
		logger.Error("ShouldBind failed %s", err)
		SendResponse(c, err, "failed to deserialize parameters", "")
		return
	}
	result := model.DB.Model(&model.TbSyntaxRule{}).Where(&model.TbSyntaxRule{ID: param.RuleId}).Update("status",
		param.Status).Limit(1)
	if result.Error != nil {
		logger.Error("update rule status failed %s,affect rows %d", result.Error.Error(), result.RowsAffected)
		SendResponse(c, result.Error, result.Error, "")
		return
	}
	SendResponse(c, nil, "ok", "")
}

// GetAllRule TODO
func GetAllRule(c *gin.Context) {
	var rs []model.TbSyntaxRule
	if err := model.DB.Find(&rs).Error; err != nil {
		logger.Error("query rules failed %s", err.Error())
		SendResponse(c, err, err.Error(), "")
		return
	}
	SendResponse(c, nil, rs, "")
}
