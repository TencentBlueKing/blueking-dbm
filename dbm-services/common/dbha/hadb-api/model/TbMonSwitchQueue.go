package model

import (
	"time"
)

// TbMonSwitchQueue TODO
type TbMonSwitchQueue struct {
	Uid                uint      `gorm:"column:uid;primary_key;AUTO_INCREMENT" json:"uid"`
	IP                 string    `gorm:"column:ip;NOT NULL" json:"ip"`
	Port               int       `gorm:"column:port;NOT NULL" json:"port"`
	ConfirmCheckTime   time.Time `gorm:"column:confirm_check_time;type:datetime;default:CURRENT_TIMESTAMP" json:"confirm_check_time"`
	DbRole             string    `gorm:"column:db_role;NOT NULL" json:"db_role"`
	SlaveIP            string    `gorm:"column:slave_ip" json:"slave_ip"`
	SlavePort          int       `gorm:"column:slave_port" json:"slave_port"`
	Status             string    `gorm:"column:status" json:"status"`
	ConfirmResult      string    `gorm:"column:confirm_result" json:"confirm_result"`
	SwitchStartTime    time.Time `gorm:"column:switch_start_time" json:"switch_start_time"`
	SwitchFinishedTime time.Time `gorm:"column:switch_finished_time" json:"switch_finished_time"`
	SwitchResult       string    `gorm:"column:switch_result" json:"switch_result"`
	Remark             string    `gorm:"column:remark" json:"remark"`
	App                string    `gorm:"column:app" json:"app"`
	DbType             string    `gorm:"column:db_type" json:"db_type"`
	Idc                string    `gorm:"column:idc" json:"idc"`
	Cloud              string    `gorm:"column:cloud" json:"cloud"`
	Cluster            string    `gorm:"column:cluster" json:"cluster"`
}

// TableName TODO
func (m *TbMonSwitchQueue) TableName() string {
	return "tb_mon_switch_queue"
}
