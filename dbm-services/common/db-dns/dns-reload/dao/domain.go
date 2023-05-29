package dao

// TbDnsBase TODO
type TbDnsBase struct {
	Uid            int64  `gorm:"column:uid" db:"column:uid" json:"uid" form:"uid"`
	App            string `gorm:"column:app" db:"column:app" json:"app" form:"app"`
	DomainName     string `gorm:"column:domain_name" db:"column:domain_name" json:"domain_name" form:"domain_name"`
	Ip             string `gorm:"column:ip" db:"column:ip" json:"ip" form:"ip"`
	Port           int64  `gorm:"column:port" db:"column:port" json:"port" form:"port"`
	StartTime      string `gorm:"column:start_time" db:"column:start_time" json:"start_time" form:"start_time"`
	LastChangeTime string `gorm:"column:last_change_time" db:"column:last_change_time" json:"last_change_time" form:"last_change_time"`
	Manager        string `gorm:"column:manager" db:"column:manager" json:"manager" form:"manager"`
	Remark         string `gorm:"column:remark" db:"column:remark" json:"remark" form:"remark"`
	DnsStr         string `gorm:"column:dns_str" db:"column:dns_str" json:"dns_str" form:"dns_str"`
	Status         string `gorm:"column:status" db:"column:status" json:"status" form:"status"`
	DomainType     int64  `gorm:"column:domain_type" db:"column:domain_type" json:"domain_type" form:"domain_type"`
	BkCloudId      string `gorm:"column:bk_cloud_id" db:"column:bk_cloud_id" json:"bk_cloud_id" form:"bk_cloud_id"`
}

// TableName TODO
func (t *TbDnsBase) TableName() string {
	return "tb_dns_base"
}

// TbDnsServer TODO
type TbDnsServer struct {
	Uid            int64  `gorm:"column:uid" db:"column:uid" json:"uid" form:"uid"`
	Ip             string `gorm:"column:ip" db:"column:ip" json:"ip" form:"ip"`
	ForwardIp      string `gorm:"column:forward_ip" db:"column:forward_ip" json:"forward_ip" form:"forward_ip"`
	Idc            string `gorm:"column:idc" db:"column:idc" json:"idc" form:"idc"`
	StartTime      string `gorm:"column:start_time" db:"column:start_time" json:"start_time" form:"start_time"`
	LastConfigTime string `gorm:"column:last_config_time" db:"column:last_config_time" json:"last_config_time" form:"last_config_time"`
	LastAlived     string `gorm:"column:last_alived" db:"column:last_alived" json:"last_alived" form:"last_alived"`
	Remark         string `gorm:"column:remark" db:"column:remark" json:"remark" form:"remark"`
	UpdateCounter  int64  `gorm:"column:update_counter" db:"column:update_counter" json:"update_counter" form:"update_counter"`
	Type           string `gorm:"column:type" db:"column:type" json:"type" form:"type"`
	Status         int64  `gorm:"column:status" db:"column:status" json:"status" form:"status"`
	BkCloudId      string `gorm:"column:bk_cloud_id" db:"column:bk_cloud_id" json:"bk_cloud_id" form:"bk_cloud_id"`
}

// TableName TODO
func (t *TbDnsServer) TableName() string {
	return "tb_dns_server"
}
