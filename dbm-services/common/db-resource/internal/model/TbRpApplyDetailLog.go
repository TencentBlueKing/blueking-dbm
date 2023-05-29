package model

import "time"

// TbRpApplyDetailLog TODO
type TbRpApplyDetailLog struct {
	ID         int       `gorm:"primaryKey;auto_increment;not null" json:"-"`
	RequestID  string    `gorm:"index:idx_request_id;column:request_id;type:varchar(64);not null" json:"request_id"` // 响应的request_id
	Item       string    `gorm:"column:item;type:varchar(64);not null" json:"item"`                                  // apply for item
	BkCloudID  int       `gorm:"column:bk_cloud_id;type:int(11);not null;comment:'云区域 ID'" json:"bk_cloud_id"`
	IP         string    `gorm:"ip;column:ip;type:varchar(20);not null" json:"ip"` //  svr ip
	BkHostID   int       `gorm:"column:bk_host_id;type:int(11);not null;comment:'bk主机ID'" json:"bk_host_id"`
	UpdateTime time.Time `gorm:"column:update_time;type:timestamp" json:"update_time"` // 最后修改时间
	CreateTime time.Time `gorm:"column:create_time;type:datetime" json:"create_time"`  // 创建时间
}

// TableName TODO
func (TbRpApplyDetailLog) TableName() string {
	return TbRpApplyDetailLogName()
}

// TbRpApplyDetailLogName TODO
func TbRpApplyDetailLogName() string {
	return "tb_rp_apply_detail_log"
}

// CreateTbRpOpsAPIDetailLog TODO
// record  log
func CreateTbRpOpsAPIDetailLog(m TbRpApplyDetailLog) error {
	return DB.Self.Table(TbRpApplyDetailLogName()).Create(&m).Error
}

// CreateBatchTbRpOpsAPIDetailLog TODO
// record  log
func CreateBatchTbRpOpsAPIDetailLog(m []TbRpApplyDetailLog) error {
	return DB.Self.Table(TbRpApplyDetailLogName()).CreateInBatches(m, len(m)).Error
}
