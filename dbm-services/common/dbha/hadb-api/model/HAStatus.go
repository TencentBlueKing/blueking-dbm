package model

import (
	"time"
)

// HaStatus struct generate by https://sql2gorm.mccode.info/
type HaStatus struct {
	Uid            uint       `gorm:"column:uid;primary_key;AUTO_INCREMENT" json:"uid"`
	IP             string     `gorm:"column:ip;NOT NULL" json:"ip"`
	Port           int        `gorm:"column:port" json:"port"`
	Module         string     `gorm:"column:module;NOT NULL" json:"module"`
	City           string     `gorm:"column:city;NOT NULL" json:"city"`
	Campus         string     `gorm:"column:campus;NOT NULL" json:"campus"`
	Cloud          string     `gorm:"column:cloud;NOT NULL" json:"cloud"`
	DbType         string     `gorm:"column:db_type" json:"db_type"`
	StartTime      *time.Time `gorm:"column:start_time;type:datetime;default:CURRENT_TIMESTAMP;NOT NULL" json:"start_time,omitempty"`
	LastTime       *time.Time `gorm:"column:last_time;type:datetime;default:CURRENT_TIMESTAMP;NOT NULL" json:"last_time,omitempty"`
	Status         string     `gorm:"column:status;NOT NULL" json:"status"`
	TakeOverGm     string     `gorm:"column:take_over_gm" json:"take_over_gm"`
	ReportInterval int        `gorm:"column:report_interval" json:"report_interval"`
}

// TableName TODO
func (m *HaStatus) TableName() string {
	return "ha_status"
}
