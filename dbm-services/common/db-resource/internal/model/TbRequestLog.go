package model

import "time"

// TbRequestLog TODO
// TbRpOpsAPILog [...]
type TbRequestLog struct {
	ID              int       `gorm:"primary_key;auto_increment;not_null" json:"-"`
	RequestID       string    `gorm:"unique;column:request_id;type:varchar(64);not null" json:"request_id"`             // 响应的request_id
	RequestUser     string    `gorm:"column:request_user;type:varchar(32);not null" json:"request_user"`                // 请求的用户
	RequestBody     string    `gorm:"column:request_body;type:json" json:"request_body"`                                // 请求体
	RequestUrl      string    `gorm:"column:request_url;type:varchar(32);not null" json:"request_url"`                  // 请求路径
	SourceIP        string    `gorm:"column:source_ip;type:varchar(32);not null" json:"source_ip"`                      // 请求来源Ip
	ResponeBody     string    `gorm:"column:respone_body;type:json" json:"respone_body"`                                // respone data message
	ResponeCode     int       `gorm:"column:respone_code;type:int(11);not null" json:"respone_code"`                    // respone code
	ResponeMesssage string    `gorm:"column:respone_messsage;type:text" json:"respone_messsage"`                        // respone data message
	UpdateTime      time.Time `gorm:"column:update_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"update_time"` // 最后修改时间
	CreateTime      time.Time `gorm:"column:create_time;type:timestamp;default:CURRENT_TIMESTAMP()" json:"create_time"` // 创建时间
}

// TableName TODO
func (TbRequestLog) TableName() string {
	return TbRequestLogName()
}

// TbRequestLogName TODO
func TbRequestLogName() string {
	return "tb_request_log"
}

// CreateTbRequestLog TODO
func CreateTbRequestLog(m TbRequestLog) (err error) {
	return DB.Self.Table(TbRequestLogName()).Create(&m).Error
}

// UpdateTbRequestLog TODO
func UpdateTbRequestLog(requestid string, updatesCols map[string]interface{}) (err error) {
	return DB.Self.Table(TbRequestLogName()).Where("request_id = ?", requestid).Updates(updatesCols).Error
}
