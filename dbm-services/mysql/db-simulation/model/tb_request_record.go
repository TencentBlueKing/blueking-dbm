package model

import (
	"strings"
	"time"
)

// TbRequestRecord TODO
type TbRequestRecord struct {
	ID          int       `gorm:"primaryKey;column:id;type:int(11);not null" json:"-"`
	RequestID   string    `gorm:"unique;column:request_id;type:varchar(64);not null" json:"request_id"` // request_id
	RequestBody string    `gorm:"column:request_body;type:json" json:"request_body"`
	UpdateTime  time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"` // 最后修改时间
	CreateTime  time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"` // 创建时间
}

// GetTableName get sql table name.获取数据库名字
func (obj *TbRequestRecord) GetTableName() string {
	return "tb_request_record"
}

// CreateRequestRecord TODO
func CreateRequestRecord(requestid, body string) (err error) {
	if strings.TrimSpace(body) == "" {
		body = "{}"
	}
	return DB.Create(&TbRequestRecord{
		RequestID:   requestid,
		RequestBody: body,
		UpdateTime:  time.Now(),
		CreateTime:  time.Now(),
	}).Error
}
