package service

import "dbm-services/mysql/priv-service/util"

// AccountName 账号名
type AccountName struct {
	User string `gorm:"column:user;" json:"user"`
}

// TbAccounts 账号表
type TbAccounts struct {
	Id          int64           `gorm:"column:id;primary_key;auto_increment" json:"id"`
	BkBizId     int64           `gorm:"column:bk_biz_id;not_null" json:"bk_biz_id"`
	ClusterType string          `gorm:"column:cluster_type;not_null" json:"cluster_type"`
	User        string          `gorm:"column:user;not_null" json:"user"`
	Psw         string          `gorm:"column:psw;not_null" json:"psw"`
	Creator     string          `gorm:"column:creator;not_null;" json:"creator"`
	CreateTime  util.TimeFormat `gorm:"column:create_time" json:"create_time"`
	Operator    string          `gorm:"column:operator" json:"operator"`
	UpdateTime  util.TimeFormat `gorm:"column:update_time" json:"update_time"`
}

// Account 账号表中需要在前端展示的字段
type Account struct {
	Id         int64           `gorm:"column:id;not_null" json:"id"`
	BkBizId    int64           `gorm:"column:bk_biz_id;not_null" json:"bk_biz_id"`
	User       string          `gorm:"column:user;not_null" json:"user"`
	Creator    string          `gorm:"column:creator;not_null;" json:"creator"`
	CreateTime util.TimeFormat `gorm:"column:create_time" json:"create_time"`
}

// MultiPsw mysql两种身份认证插件mysql_old_password、mysql_native_password生成的密码
type MultiPsw struct {
	OldPsw string `json:"old_psw"`
	Psw    string `json:"psw"`
}

// AccountPara GetAccount、AddAccount、ModifyAccountPassword、DeleteAccount函数的入参
type AccountPara struct {
	Id          int64   `json:"id"`
	BkBizId     int64   `json:"bk_biz_id"`
	User        string  `json:"user"`
	Psw         string  `json:"psw"`
	Operator    string  `json:"operator"`
	ClusterType *string `json:"cluster_type" `
	MigrateFlag bool    `json:"migrate_flag"`
}

// PrivLog 记录权限相关接口的调用日志
type PrivLog struct {
	Id       int64           `gorm:"column:id;primary_key;auto_increment" json:"id"`
	BkBizId  int64           `gorm:"column:bk_biz_id;not_null" json:"bk_biz_id"`
	Operator string          `gorm:"column:operator" json:"operator"`
	Para     string          `gorm:"column:para" json:"para"`
	Time     util.TimeFormat `gorm:"column:execute_time" json:"execute_time"`
}
