package model

import (
	"encoding/json"
	"time"
)

const (
	// Consumed TODO
	Consumed = "consumed"
	// Imported TODO
	Imported = "imported"
)

// TbRpOperationInfo TODO
type TbRpOperationInfo struct {
	ID            int             `gorm:"primaryKey;auto_increment;not null" json:"-"`
	RequestID     string          `gorm:"index:idx_request_id;column:request_id;type:varchar(64);not null" json:"request_id"`
	TotalCount    int             `gorm:"column:total_count;type:int(11);comment:'task Id'" json:"total_count"`
	BkHostIds     json.RawMessage `gorm:"column:bk_host_ids;type:json;comment:'主机Id'" json:"bk_host_ids"`
	IpList        json.RawMessage `gorm:"column:ip_list;type:json;comment:'主机ip'" json:"ip_list"`
	OperationType string          `gorm:"column:operation_type;type:varchar(64);not null;comment:'operation type'" json:"operation_type"`
	Operator      string          `gorm:"column:operator;type:varchar(64);not null;comment:'operator user'" json:"operator"`
	Status        string          `gorm:"column:status;type:varchar(64);not null;comment:'operator user'" json:"-"`
	TaskId        string          `gorm:"column:task_id;type:varchar(128);not null;comment:'task Id'" json:"task_id"`
	BillId        string          `gorm:"column:bill_id;type:varchar(128);not null;comment:'bill Id'" json:"bill_id"`
	UpdateTime    time.Time       `gorm:"column:update_time;type:timestamp" json:"update_time"` // 最后修改时间
	CreateTime    time.Time       `gorm:"column:create_time;type:datetime" json:"create_time"`  // 创建时间
}

// TableName TODO
func (TbRpOperationInfo) TableName() string {
	return TbRpOperationInfoTableName()
}

// TbRpOperationInfoTableName TODO
func TbRpOperationInfoTableName() string {
	return "tb_rp_operation_info"
}
