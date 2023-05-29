package model

import (
	"time"
)

// DbStatus TODO
type DbStatus struct {
	Uid      uint      `gorm:"column:uid;primary_key;AUTO_INCREMENT" json:"uid"`
	AgentIP  string    `gorm:"column:agent_ip;NOT NULL" json:"agent_ip"`
	IP       string    `gorm:"column:ip;NOT NULL" json:"ip"`
	Port     uint      `gorm:"column:port;NOT NULL" json:"port"`
	DbType   string    `gorm:"column:db_type;NOT NULL" json:"db_type"`
	Status   string    `gorm:"column:status;NOT NULL" json:"status"`
	Cloud    string    `gorm:"column:cloud;NOT NULL" json:"cloud"`
	LastTime time.Time `gorm:"column:last_time;type:datetime;default:CURRENT_TIMESTAMP;NOT NULL"`
}

// TableName TODO
func (m *DbStatus) TableName() string {
	return "db_status"
}
