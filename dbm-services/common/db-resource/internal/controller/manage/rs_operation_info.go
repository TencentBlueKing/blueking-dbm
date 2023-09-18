package manage

import (
	"fmt"

	"dbm-services/common/db-resource/internal/model"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

// GetOperationInfoParam TODO
type GetOperationInfoParam struct {
	OperationType string   `json:"operation_type"`
	BillIds       []string `json:"bill_ids"`
	TaskIds       []string `json:"task_ids"`
	Operator      string   `json:"operator"`
	BeginTime     string   `json:"begin_time"  binding:"omitempty,datetime=2006-01-02 15:04:05" `
	EndTime       string   `json:"end_time"  binding:"omitempty,datetime=2006-01-02 15:04:05"`
	Limit         int      `json:"limit"`
	Offset        int      `json:"offset"`
}

// OperationInfoList TODO
func (o MachineResourceHandler) OperationInfoList(r *gin.Context) {
	var input GetOperationInfoParam
	requestId := r.GetString("request_id")
	if err := o.Prepare(r, &input); err != nil {
		logger.Error(fmt.Sprintf("Preare Error %s", err.Error()))
		return
	}
	db := model.DB.Self.Table(model.TbRpOperationInfoTableName())
	input.query(db)
	var data []model.TbRpOperationInfo
	if err := db.Scan(&data).Error; err != nil {
		o.SendResponse(r, err, err.Error(), requestId)
		return
	}
	var count int64
	if err := db.Count(&count).Error; err != nil {
		o.SendResponse(r, err, requestId, err.Error())
		return
	}
	o.SendResponse(r, nil, map[string]interface{}{"details": data, "count": count}, requestId)
}

func (p GetOperationInfoParam) query(db *gorm.DB) {
	if len(p.BillIds) > 0 {
		db.Where("bill_id in (?)", p.BillIds)
	}
	if len(p.TaskIds) > 0 {
		db.Where("task_id in (?)", p.TaskIds)
	}
	if cmutil.IsNotEmpty(p.Operator) {
		db.Where("operator = ?", p.Operator)
	}
	if cmutil.IsNotEmpty(p.OperationType) {
		db.Where("operation_type = ? ", p.OperationType)
	}
	if cmutil.IsNotEmpty(p.EndTime) {
		db.Where("create_time <= ? ", p.EndTime)
	}
	if cmutil.IsNotEmpty(p.BeginTime) {
		db.Where("create_time >= ? ", p.BeginTime)
	}
	if p.Limit > 0 {
		db.Offset(p.Offset).Limit(p.Limit)
	}
}
