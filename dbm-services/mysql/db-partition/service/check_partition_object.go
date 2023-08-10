package service

import (
	"sync"
	"time"
)

// DiffOneDay TODO
const DiffOneDay = 1 // 分区名称与分区描述相差的天数

// Checker TODO
type Checker struct {
	ClusterType  string `json:"cluster_type"`
	BkBizId      int    `json:"bk_biz_id"`
	ConfigId     int    `json:"config_id"`
	ClusterId    int    `json:"cluster_id"`
	ImmuteDomain string `json:"immute_domain"`
	Port         int    `json:"port"`
	BkCloudId    *int   `json:"bk_cloud_id"`
}

// PartitionSqlSet 分区语句集合
type PartitionSqlSet struct {
	Mu            sync.RWMutex
	PartitionSqls []PartitionSql
}

// PartitionSql 实例ip:port上的分区语句
type PartitionSql struct {
	ConfigId      int       `json:"config_id"`
	DbLike        string    `json:"dblike"`
	TbLike        string    `json:"tblike"`
	InitPartition []InitSql `json:"init_partition"`
	AddPartition  []string  `json:"add_partition"`
	DropPartition []string  `json:"drop_partition"`
}

// PartitionCronLog TODO
type PartitionCronLog struct {
	Id           int    `json:"id" gorm:"column:id;primary_key;auto_increment"`
	BkBizId      int    `json:"bk_biz_id" gorm:"column:bk_biz_id"`
	ClusterId    int    `json:"cluster_id" gorm:"column:cluster_id"`
	ConfigId     int    `json:"config_id" gorm:"column:config_id"`
	TicketId     int    `json:"ticket_id" gorm:"column:ticket_id"`
	ImmuteDomain string `json:"immute_domain" gorm:"column:immute_domain"`
	Scheduler    string `json:"scheduler" gorm:"column:scheduler"`
	BkCloudId    int    `json:"bk_cloud_id" gorm:"column:bk_cloud_id"`
	TimeZone     string `json:"time_zone" gorm:"column:time_zone"`
	CronDate     string `json:"cron_date" grom:"column:cron_date"`
	CheckInfo    string `json:"check_info" gorm:"column:check_info"`
	Status       string `json:"status" gorm:"column:status"`
}

type CreatePartitionCronLog struct {
	PartitionCronLog
	ClusterType string `json:"cluster_type"`
}

// PartitionLog TODO
type PartitionLog struct {
	Id          int       `json:"id"`
	TicketId    int       `json:"ticket_id" gorm:"column:ticket_id"`
	ExecuteTime time.Time `json:"execute_time" gorm:"execute_time"`
	CheckInfo   string    `json:"check_info" gorm:"check_info"`
	Status      string    `json:"status" gorm:"status"`
}

// InitMessages TODO
type InitMessages struct {
	mu   sync.RWMutex
	list []InitSql
}

// InitSql TODO
type InitSql struct {
	Sql      string `json:"sql"`
	NeedSize int    `json:"need_size"`
}

// Messages TODO
type Messages struct {
	mu   sync.RWMutex
	list []string
}
