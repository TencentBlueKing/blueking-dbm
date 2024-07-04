package service

import (
	"sync"
	"time"
)

// DiffOneDay TODO
const DiffOneDay = 1 // 分区名称与分区描述相差的天数

// Checker 检查分区规则是否需要需要被实施
type Checker struct {
	ClusterType  string `json:"cluster_type"`
	BkBizId      int    `json:"bk_biz_id"`
	DbAppAbbr    string `json:"db_app_abbr"`
	BkBizName    string `json:"bk_biz_name"`
	ConfigId     int    `json:"config_id"`
	ClusterId    int    `json:"cluster_id"`
	ImmuteDomain string `json:"immute_domain"`
	Port         int    `json:"port"`
	BkCloudId    *int   `json:"bk_cloud_id"`
	FromCron     bool   `json:"from_cron"` // 由定时任务发起
}

// PartitionSqlSet 分区语句集合
type PartitionSqlSet struct {
	Mu            sync.RWMutex
	PartitionSqls []PartitionSql `json:"partition_sqls"`
}

// ConfigSet 配置集合
type ConfigSet struct {
	Mu      sync.RWMutex
	Configs []PartitionConfig `json:"configs"`
}

// ConfigIdLogSet 分区配置ID以及其日志集合
type ConfigIdLogSet struct {
	Mu     sync.RWMutex
	IdLogs []IdLog `json:"logs"`
}

// IdLog 分区配置ID以及其日志
type IdLog struct {
	ConfigId int    `json:"config_id"`
	Log      string `json:"log"`
}

// PartitionSql 实例ip:port上的分区语句
type PartitionSql struct {
	ConfigId int    `json:"config_id"`
	DbLike   string `json:"dblike"`
	TbLike   string `json:"tblike"`
	// 初始化分区表
	InitPartition []InitSql `json:"init_partition"`
	// 添加分区
	AddPartition []string `json:"add_partition"`
	// 删除分区
	DropPartition []string `json:"drop_partition"`
}

// PartitionCronLog 分区的定时任务日志表
type PartitionCronLog struct {
	Id        int    `json:"id" gorm:"column:id;primary_key;auto_increment"`
	ConfigId  int    `json:"config_id" gorm:"column:config_id"`
	Scheduler string `json:"scheduler" gorm:"column:scheduler"`
	CronDate  string `json:"cron_date" grom:"column:cron_date"`
	CheckInfo string `json:"check_info" gorm:"column:check_info"`
	Status    string `json:"status" gorm:"column:status"`
}

// CreatePartitionCronLog 分区的定时任务日志表，区分集群类型
type CreatePartitionCronLog struct {
	Logs        []PartitionCronLog `json:"logs"`
	ClusterType string             `json:"cluster_type"`
}

// PartitionLog 分区日志
type PartitionLog struct {
	Id          int       `json:"id"`
	ExecuteTime time.Time `json:"execute_time" gorm:"execute_time"`
	CheckInfo   string    `json:"check_info" gorm:"check_info"`
	Status      string    `json:"status" gorm:"status"`
}

// InitMessages 初始化分区的sql数组以及其互斥锁
type InitMessages struct {
	mu   sync.RWMutex
	list []InitSql
}

// InitSql 初始化分区的sql
type InitSql struct {
	Sql          string `json:"sql"`
	NeedSize     int    `json:"need_size"`
	HasUniqueKey bool   `json:"has_unique_key"`
}

// Messages 数组以及其互斥锁
type Messages struct {
	mu   sync.RWMutex
	list []string
}

type Host struct {
	Ip        string `json:"ip"`
	Port      int    `json:"port"`
	BkCloudId int    `json:"bk_cloud_id"`
}
