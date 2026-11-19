package entity

import "time"

// 域名操作类型
const (
	OpTypeCreateDomain  = "CREATE_DOMAIN"  // 创建域名
	OpTypeUpdateManager = "UPDATE_MANAGER" // 修改负责人
	OpTypeUpdateRemark  = "UPDATE_REMARK"  // 修改备注
	OpTypeUpdateIp      = "UPDATE_IP"      // 修改IP
	OpTypeDeleteDomain  = "DELETE_DOMAIN"  // 删除域名
)

// TbDnsOpLog 域名操作日志表
type TbDnsOpLog struct {
	Uid        int64     `gorm:"column:uid;size:20;primary_key;AUTO_INCREMENT" json:"uid"`
	OpTime     time.Time `gorm:"column:op_time" json:"op_time"`
	Operator   string    `gorm:"size:64;column:operator" json:"operator"`
	ClientIp   string    `gorm:"size:64;column:client_ip" json:"client_ip"`
	OpType     string    `gorm:"size:32;column:op_type" json:"op_type"`
	DomainName string    `gorm:"size:255;column:domain_name" json:"domain_name"`
	Content    string    `gorm:"type:text;column:content" json:"content"`
}

// TableName tb_dns_op_log
func (t *TbDnsOpLog) TableName() string {
	return "tb_dns_op_log"
}

// Columns tb_dns_op_log col
func (t *TbDnsOpLog) Columns() []string {
	return []string{"uid", "op_time", "operator", "client_ip", "op_type", "domain_name", "content"}
}
