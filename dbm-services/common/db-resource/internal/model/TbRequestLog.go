package model

import (
	"context"
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// TbRequestLog 请求日志表
// TbRpOpsAPILog [...]
// nolint
type TbRequestLog struct {
	ID              int       `gorm:"primary_key;auto_increment;not_null" json:"-"`
	RequestID       string    `gorm:"unique;column:request_id;type:varchar(64);not null" json:"request_id"`             // 响应的request_id
	RequestUser     string    `gorm:"column:request_user;type:varchar(32);not null" json:"request_user"`                // 请求的用户
	RequestBody     string    `gorm:"column:request_body;type:json" json:"request_body"`                                // 请求体
	RequestUrl      string    `gorm:"column:request_url;type:varchar(32);not null" json:"request_url"`                  // 请求路径
	SourceIP        string    `gorm:"column:source_ip;type:varchar(32);not null" json:"source_ip"`                      // 请求来源Ip
	ResponseBody    string    `gorm:"column:response_body;type:json" json:"response_body"`                              // response data message
	ResponseCode    int       `gorm:"column:response_code;type:int(11);not null" json:"response_code"`                  // response code
	ResponseMessage string    `gorm:"column:response_message;type:text" json:"response_message"`                        // response data message
	UpdateTime      time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"` // 最后修改时间
	CreateTime      time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"` // 创建时间
}

// TableName table name
func (TbRequestLog) TableName() string {
	return TbRequestLogName()
}

// TbRequestLogName TODO
func TbRequestLogName() string {
	return "tb_request_log"
}

// CreateTbRequestLog insert a request record
func CreateTbRequestLog(m TbRequestLog) (err error) {
	return DB.Self.Table(TbRequestLogName()).Create(&m).Error
}

// UpdateTbRequestLog update request a record
func UpdateTbRequestLog(requestid string, updatesCols map[string]interface{}) (err error) {
	return DB.Self.Table(TbRequestLogName()).Where("request_id = ?", requestid).Updates(updatesCols).Error
}

// QueryResourceParamByBillOrTask query resource operation parameters by bill_id or task_id
// This function does not depend on view v_request_by_bill, it uses raw SQL with JSON_EXTRACT
func QueryResourceParamByBillOrTask(ctx context.Context, billID, taskID string, limit, offset int) ([]string, error) {
	if billID == "" && taskID == "" {
		return nil, fmt.Errorf("bill_id and task_id cannot both be empty")
	}

	// Set default limit
	if limit <= 0 {
		limit = 100
	}
	if offset < 0 {
		offset = 0
	}

	// Record start time for slow query logging
	startTime := time.Now()

	// Build the query with JSON_EXTRACT for filtering
	// Using parameterized query to prevent SQL injection
	query := DB.Self.WithContext(ctx).Table(TbRequestLogName()).
		Select("request_body")

	// Build WHERE conditions with OR logic
	conditions := []string{}
	params := []interface{}{}

	if billID != "" {
		conditions = append(conditions, "JSON_EXTRACT(request_body, '$.bill_id') = ?")
		params = append(params, billID)
	}
	if taskID != "" {
		conditions = append(conditions, "JSON_EXTRACT(request_body, '$.task_id') = ?")
		params = append(params, taskID)
	}

	// Apply OR logic
	if len(conditions) > 0 {
		whereClause := ""
		for i, cond := range conditions {
			if i > 0 {
				whereClause += " OR "
			}
			whereClause += cond
		}
		query = query.Where(whereClause, params...)
	}

	// Apply pagination and ordering
	query = query.Order("create_time DESC").
		Limit(limit).
		Offset(offset)

	// Execute the query
	var requestBodies []string
	if err := query.Pluck("request_body", &requestBodies).Error; err != nil {
		return nil, fmt.Errorf("failed to query request logs: %w", err)
	}

	// Check for slow query (threshold: 1 second)
	duration := time.Since(startTime)
	if duration > time.Second {
		logger.Warn("slow query detected: QueryResourceParamByBillOrTask took %v, bill_id=%s, task_id=%s, limit=%d, offset=%d",
			duration, billID, taskID, limit, offset)
	}

	return requestBodies, nil
}
