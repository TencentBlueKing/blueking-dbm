package model

import "time"

// TbRpReturnDetail [...]
type TbRpReturnDetail struct {
	ID         int       `gorm:"primaryKey;column:id;type:int(11);not null" json:"-"`
	IP         string    `gorm:"column:ip;type:varchar(20);not null" json:"ip"`               // macheine ip
	User       string    `gorm:"column:user;type:varchar(32);not null" json:"user"`           // 请求的用户
	FromSys    string    `gorm:"column:from_sys;type:varchar(32);not null" json:"from_sys"`   // 来着哪个系统
	ApplyFor   string    `gorm:"column:apply_for;type:varchar(32);not null" json:"apply_for"` // 资源类型 proxy|tendis|tendb ...
	Desc       string    `gorm:"column:desc;type:varchar(1024);not null" json:"desc"`         // 描述
	UpdateTime time.Time `gorm:"column:update_time;type:timestamp" json:"update_time"`        // 最后修改时间
	CreateTime time.Time `gorm:"column:create_time;type:datetime" json:"create_time"`         // 创建时间
}

// TbRpReturnDetailName TODO
func TbRpReturnDetailName() string {
	return "tb_rp_return_detail"
}

// BatchCreateTbRpReturnDetail TODO
func BatchCreateTbRpReturnDetail(m []TbRpReturnDetail) error {
	return DB.Self.Table(TbRpReturnDetailName()).CreateInBatches(m, len(m)).Error
}
