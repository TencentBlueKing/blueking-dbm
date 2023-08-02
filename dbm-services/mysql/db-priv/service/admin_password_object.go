package service

import "dbm-services/mysql/priv-service/util"

// ModifyAdminUserPasswordPara 函数的入参
type ModifyAdminUserPasswordPara struct {
	UserName         *string         `json:"username"`
	Psw              string          `json:"password"`
	LockUntil        util.TimeFormat `json:"lock_until"`
	Operator         string          `json:"operator"`
	Clusters         []OneCluster    `json:"clusters"`
	SecurityRuleName string          `json:"security_rule_name"`
	Range            string          `json:"range"`
	Async            bool            `json:"async"` // 是否异步的方式执行
}

// ModifyPasswordPara 函数的入参
type ModifyPasswordPara struct {
	UserName         *string   `json:"username"`
	Psw              string    `json:"password"`
	Operator         string    `json:"operator"`
	Instances        []Address `json:"instances"`
	SecurityRuleName string    `json:"security_rule_name"`
}

// GetPasswordPara 函数的入参
type GetPasswordPara struct {
	Instances []Address `json:"instances"`
	UserName  *string   `json:"username"`
}

type TbPasswords struct {
	Id         int64           `gorm:"column:id;primary_key;auto_increment" json:"id"`
	Ip         string          `gorm:"column:ip;not_null" json:"ip"`
	Port       int64           `gorm:"column:port;not_null" json:"port"`
	Password   string          `gorm:"column:password;not_null" json:"password"`
	UserName   string          `gorm:"column:username;not_null" json:"username"`
	LockUntil  util.TimeFormat `gorm:"column:lock_until" json:"lock_until"`
	Operator   string          `gorm:"column:operator" json:"operator"`
	UpdateTime util.TimeFormat `gorm:"column:update_time" json:"update_time"`
}

type OneCluster struct {
	BkCloudId              *int64         `json:"bk_cloud_id"`
	ClusterType            *string        `json:"cluster_type"`
	MultiRoleInstanceLists []InstanceList `json:"instances"`
}

type InstanceList struct {
	// 对于修改密码的接口，仅当集群为tendbcluster类型，需要再根据role判断实施方式
	// Role用于区分spider、tdbctl、remote
	Role      string    `json:"role"`
	Addresses []Address `json:"addresses"`
}

type Address struct {
	Ip   string `gorm:"column:ip" json:"ip"`
	Port int64  `gorm:"column:port" json:"port"`
}

type BatchResult struct {
	Success []Address `json:"success"`
	Fail    []Address `json:"fail"`
}

type AdminPasswordResp struct {
	Locked   []*TbPasswords `json:"locked"`
	Unlocked []*TbPasswords `json:"unlocked"`
}

type Password struct {
	Password string `gorm:"column:password;not_null" json:"password"`
}
