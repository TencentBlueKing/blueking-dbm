package model

import "time"

// SwitchLogs TODO
type SwitchLogs struct {
	UID      int        `gorm:"column:uid;primaryKey;autoIncrement" json:"uid"`
	SwitchID int        `gorm:"column:sw_id" json:"sw_id"`
	IP       string     `gorm:"column:ip" json:"ip"`
	Result   string     `gorm:"column:result" json:"result"`
	Datetime *time.Time `gorm:"column:datetime" json:"datetime,omitempty"`
	Comment  string     `gorm:"column:comment" json:"comment"`
	Port     int        `gorm:"column:port" json:"port"`
}

// TableName TODO
func (s *SwitchLogs) TableName() string {
	return "switch_logs"
}
