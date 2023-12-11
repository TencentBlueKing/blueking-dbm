package service

import (
	"time"
)

// ModifyAdminUserPasswordPara 函数的入参
type ModifyAdminUserPasswordPara struct {
	UserName  string `json:"username"`
	Component string `json:"component"`
	Psw       string `json:"password"`
	//LockUntil        time.Time `json:"lock_until"`
	LockHour         int          `json:"lock_hour"`
	Operator         string       `json:"operator"`
	Clusters         []OneCluster `json:"clusters"`
	SecurityRuleName string       `json:"security_rule_name"`
	Range            string       `json:"range"`
	Async            bool         `json:"async"` // 是否异步的方式执行
}

// ModifyPasswordPara 函数的入参
type ModifyPasswordPara struct {
	UserName         string    `json:"username"`
	Component        string    `json:"component"`
	Psw              string    `json:"password"`
	Operator         string    `json:"operator"`
	Instances        []Address `json:"instances"`
	SecurityRuleName string    `json:"security_rule_name"`
	InitPlatform     bool      `json:"init_platform"`
}

// GetPasswordPara 函数的入参
type GetPasswordPara struct {
	Instances []Address         `json:"instances"`
	Users     []UserInComponent `json:"users"`
	Limit     *int              `json:"limit"`
	Offset    *int              `json:"offset"`
	BeginTime string            `json:"begin_time"`
	EndTime   string            `json:"end_time"`
}

type UserInComponent struct {
	UserName  string `json:"username"`
	Component string `json:"component"`
}

// GetAdminUserPasswordPara 函数的入参
type GetAdminUserPasswordPara struct {
	Instances []IpPort `json:"instances"`
	UserName  string   `json:"username"`
	Component string   `json:"component"`
	Limit     *int     `json:"limit"`
	Offset    *int     `json:"offset"`
	BeginTime string   `json:"begin_time"`
	EndTime   string   `json:"end_time"`
}

type TbPasswords struct {
	Ip        string `gorm:"column:ip;not_null" json:"ip"`
	Port      int64  `gorm:"column:port;not_null" json:"port"`
	BkCloudId int64  `gorm:"column:bk_cloud_id" json:"bk_cloud_id"`
	// UserName 用户名
	UserName string `gorm:"column:username;not_null" json:"username"`
	// Password 加密后的密码
	Password string `gorm:"column:password;not_null" json:"password"`
	// Component 组件，比如mysql、proxy
	Component  string    `gorm:"column:component;not_null" json:"component"`
	LockUntil  time.Time `gorm:"column:lock_until" json:"lock_until"`
	Operator   string    `gorm:"column:operator" json:"operator"`
	UpdateTime time.Time `gorm:"column:update_time" json:"update_time"`
}

type OneCluster struct {
	BkCloudId              *int64         `json:"bk_cloud_id"`
	ClusterType            *string        `json:"cluster_type"`
	MultiRoleInstanceLists []InstanceList `json:"instances"`
}

type InstanceList struct {
	// 对于修改密码的接口，仅当集群为tendbcluster类型，需要再根据role判断实施方式
	// Role用于区分spider、tdbctl、remote
	Role      string   `json:"role"`
	Addresses []IpPort `json:"addresses"`
}
type IpPort struct {
	Ip   string `gorm:"column:ip;not_null" json:"ip"`
	Port int64  `gorm:"column:port;not_null" json:"port"`
}

type Address struct {
	Ip        string `gorm:"column:ip" json:"ip"`
	Port      int64  `gorm:"column:port" json:"port"`
	BkCloudId *int64 `gorm:"column:bk_cloud_id" json:"bk_cloud_id"`
}

type BatchResult struct {
	Success []OneCluster `json:"success"`
	Fail    []OneCluster `json:"fail"`
}

type AdminPasswordResp struct {
	Locked   []*TbPasswords `json:"locked"`
	Unlocked []*TbPasswords `json:"unlocked"`
}

type Password struct {
	Password string `gorm:"column:password;not_null" json:"password"`
}

type PlatformPara struct {
	DbConfig string `json:"db_config"`
}
