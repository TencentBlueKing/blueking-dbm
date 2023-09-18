package entity

import (
	"time"
)

/*
	GCS DNS 表相关
| tb_dns_alias                |			-----   域名别名表
| tb_dns_base                 |			-----	域名表
| tb_dns_config               |			-----	域名配置表
| tb_dns_forward_config       |
| tb_dns_forward_info         |
| tb_dns_idc_map              |			-----	域名地区映射表
| tb_dns_multi                |
| tb_dns_op_log               |
| tb_dns_server               |			-----	域名服务相关机器表
| tb_dns_tencent_idc_svr      |
| tb_dns_type                 |
| tb_dns_zone_info            |
*/

// TbDnsBase 域名表
type TbDnsBase struct {
	Uid            int64     `gorm:"column:uid;size:11;primary_key;AUTO_INCREMENT"  json:"uid"`
	App            string    `gorm:"size:32;column:app" json:"app"`
	DomainName     string    `gorm:"size:64;column:domain_name" json:"domain_name"`
	Ip             string    `gorm:"size:20;column:ip" json:"ip"`
	Port           int       `gorm:"size:11;column:port" json:"port"`
	StartTime      time.Time `gorm:"column:start_time" json:"start_time"`
	LastChangeTime time.Time `gorm:"column:last_change_time" json:"last_change_time"`
	Manager        string    `gorm:"size:32;column:manager" json:"manager"`
	Remark         string    `gorm:"size:128;column:remark" json:"remark"`
	DnsStr         string    `gorm:"size:128;column:dns_str" json:"dns_str"`
	Status         string    `gorm:"size:10;column:status" json:"status"`
	DomainType     int64     `gorm:"size:11;column:domain_type" json:"domain_type"`
	BkCloudId      int64     `gorm:"size:32;column:bk_cloud_id" json:"bk_cloud_id"`
}

// TableName TODO
func (t *TbDnsBase) TableName() string {
	return "tb_dns_base"
}

// Columns TODO
func (t *TbDnsBase) Columns() []string {
	return []string{"uid", "app", "domain_name", "ip", "port", "start_time", "last_change_time", "manager", "remark",
		"dns_str", "status", "domain_type", "bk_cloud_id"}
}

// TableIndex 索引
func (t *TbDnsBase) TableIndex() [][]string {
	return [][]string{
		[]string{"ip", "port"},
		[]string{"domain_name", "app"},
		[]string{"app", "manager"},
	}
}

// TableUnique 唯一索引
func (t *TbDnsBase) TableUnique() [][]string {
	return [][]string{
		[]string{"domain_name", "ip", "port"},
	}
}

// TbDnsServer 服务器表
type TbDnsServer struct {
	Uid            int64     `gorm:"column:uid;size:11;primary_key;AUTO_INCREMENT"  json:"uid"`
	Ip             string    `gorm:"column:ip;size:20" json:"ip"`
	ForwardIp      string    `gorm:"column:forward_ip;size:100" json:"forward_ip"`
	Idc            string    `gorm:"column:idc;size:64" json:"idc"`
	StartTime      time.Time `gorm:"column:start_time" json:"start_time"`
	LastConfigTime time.Time `gorm:"column:last_config_time" json:"last_config_time"`
	LastAlived     time.Time `gorm:"column:last_alived" json:"last_alived"`
	Remark         string    `gorm:"column:remark;size:128" json:"remark"`
	UpdateCounter  int64     `gorm:"column:update_counter;size:20" json:"update_counter"`
	Type           string    `gorm:"column:type;size:64" json:"type" form:"type"`
	Status         int64     `gorm:"column:status;size:11" json:"status" form:"status"`
	BkCloudId      int64     `gorm:"size:32;column:bk_cloud_id" json:"bk_cloud_id"`
}

// TableName TODO
func (t *TbDnsServer) TableName() string {
	return "tb_dns_server"
}

// Columns TODO
func (t *TbDnsServer) Columns() []string {
	return []string{"uid", "ip", "forward_ip", "idc", "start_time", "last_config_time", "last_alived", "remark",
		"update_counter", "type", "status"}
}

// TbDnsIdcMap 地区映射表
type TbDnsIdcMap struct {
	Uid       int64  `gorm:"column:uid;size:11;primary_key;AUTO_INCREMENT"  json:"uid"`
	Oidc      string `gorm:"column:oidc;size:64" json:"oidc"`
	Nidc      string `gorm:"column:nidc;size:64" json:"nidc"`
	Status    int64  `gorm:"column:status;size:11" json:"status" form:"status"`
	BkCloudId int64  `gorm:"size:32;column:bk_cloud_id" json:"bk_cloud_id"`
}

// TableName TODO
func (t *TbDnsIdcMap) TableName() string {
	return "tb_dns_idc_map"
}
