package entity

import "time"

// TbDnsDomainInfo 域名级别的公共属性表。数据由 tb_dns_base 按域名联动产生
type TbDnsDomainInfo struct {
	Uid        int64  `gorm:"column:uid;size:20;primary_key;AUTO_INCREMENT" json:"uid"`
	DomainName string `gorm:"size:255;column:domain_name" json:"domain_name"`
	// Manager 管理人，支持多个，英文逗号分隔，如 "zhangsan,lisi"
	Manager string `gorm:"size:512;column:manager" json:"manager"`
	// Remark 域名维度的备注
	Remark     string    `gorm:"size:512;column:remark" json:"remark"`
	Updater    string    `gorm:"size:64;column:updater" json:"updater"`
	UpdateTime time.Time `gorm:"column:update_time" json:"update_time"`
}

// TableName tb_dns_domain_info
func (t *TbDnsDomainInfo) TableName() string {
	return "tb_dns_domain_info"
}

// Columns tb_dns_domain_info col
func (t *TbDnsDomainInfo) Columns() []string {
	return []string{"uid", "domain_name", "manager", "remark", "updater", "update_time"}
}

// TableUnique 唯一索引
func (t *TbDnsDomainInfo) TableUnique() [][]string {
	return [][]string{
		[]string{"domain_name"},
	}
}
