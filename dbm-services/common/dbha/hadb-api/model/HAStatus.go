package model

import (
	"time"
)

// HaStatus struct generate by https://sql2gorm.mccode.info/
type HaStatus struct {
	Uid            uint       `gorm:"column:uid;type:bigint;primary_key;AUTO_INCREMENT" json:"uid,omitempty"`
	IP             string     `gorm:"column:ip;type:varchar(32);index:idx_ip_module_type;NOT NULL" json:"ip,omitempty"`
	Port           int        `gorm:"column:port;type:int(11)" json:"port,omitempty"`
	Module         string     `gorm:"column:module;type:varchar(32);index:idx_ip_module_type;NOT NULL" json:"module,omitempty"`
	DbType         string     `gorm:"column:db_type;type:varchar(32);index:idx_ip_module_type;" json:"db_type,omitempty"`
	CityID         int        `gorm:"column:city_id;type:int(11);NOT NULL;default:0" json:"city_id,omitempty"`
	Campus         string     `gorm:"column:campus;type:varchar(32);NOT NULL" json:"campus,omitempty"`
	CloudID        int        `gorm:"column:cloud_id;type:int(11);NOT NULL;default:0" json:"cloud_id,omitempty"`
	StartTime      *time.Time `gorm:"column:start_time;type:datetime;default:CURRENT_TIMESTAMP;NOT NULL" json:"start_time,omitempty"`
	LastTime       *time.Time `gorm:"column:last_time;type:datetime;default:CURRENT_TIMESTAMP;NOT NULL" json:"last_time,omitempty"`
	Status         string     `gorm:"column:status;type:varchar(32);NOT NULL" json:"status,omitempty"`
	TakeOverGm     string     `gorm:"column:take_over_gm;type:varchar(32)" json:"take_over_gm,omitempty"`
	ReportInterval int        `gorm:"column:report_interval;type:tinyint" json:"report_interval,omitempty"`
}

// TableName TODO
func (m *HaStatus) TableName() string {
	return "ha_status"
}
