package service

import (
	"dbm-services/mysql/priv-service/util"
)

// TbAccountRules 账号规则表
type TbAccountRules struct {
	Id         int64           `gorm:"column:id;primary_key;auto_increment" json:"id"`
	BkBizId    int64           `gorm:"column:bk_biz_id;not_null" json:"bk_biz_id"`
	AccountId  int64           `gorm:"column:account_id;not_null" json:"account_id"`
	Dbname     string          `gorm:"column:dbname;not_null" json:"dbname"`
	Priv       string          `gorm:"column:priv;not_null" json:"priv"`
	DmlDdlPriv string          `gorm:"column:dml_ddl_priv;not_null" json:"dml_ddl_priv"`
	GlobalPriv string          `gorm:"column:global_priv;not_null" json:"global_priv"`
	Creator    string          `gorm:"column:creator;not_null;" json:"creator"`
	CreateTime util.TimeFormat `gorm:"column:create_time" json:"create_time"`
	Operator   string          `gorm:"column:operator" json:"operator"`
	UpdateTime util.TimeFormat `gorm:"column:update_time" json:"update_time"`
}

// Rule 账号规则表中需要在前端展示的字段
type Rule struct {
	Id         int64           `gorm:"column:id;primary_key;auto_increment" json:"id"`
	AccountId  int64           `gorm:"column:account_id;not_null" json:"account_id"`
	BkBizId    int64           `gorm:"column:bk_biz_id;not_null" json:"bk_biz_id"`
	Dbname     string          `gorm:"column:dbname;not_null" json:"dbname"`
	Priv       string          `gorm:"column:priv;not_null" json:"priv"`
	Creator    string          `gorm:"column:creator;not_null;" json:"creator"`
	CreateTime util.TimeFormat `gorm:"column:create_time" json:"create_time"`
}

// AccountRuleSplitUser 账号与账号规则表中需要在前端展示的内容
type AccountRuleSplitUser struct {
	Account *Account `json:"account"`
	Rules   []*Rule  `json:"rules"`
}

// DeleteAccountRuleById 根据账号规则表中id，删除账号规则
type DeleteAccountRuleById struct {
	BkBizId  int64  `json:"bk_biz_id"`
	Operator string `json:"operator"`
	Id       []int  `json:"id"`
}

// AccountRulePara AddAccountRule、ModifyAccountRule、ParaPreCheck函数的入参
type AccountRulePara struct {
	BkBizId   int64  `json:"bk_biz_id"`
	Id        int64  `json:"id"`         // account rule的id
	AccountId int64  `json:"account_id"` // account的id
	Dbname    string `json:"dbname"`
	// key为dml、ddl、global；value为逗号分隔的权限；示例{"dml":"select,update","ddl":"create","global":"REPLICATION SLAVE"}
	Priv     map[string]string `json:"priv"`
	Operator string            `json:"operator"`
}
