// Package service TODO
package service

import (
	"time"
)

// PartitionConfig 分区配置表
type PartitionConfig struct {
	ID                  int    `json:"id" gorm:"column:id;primary_key;auto_increment"`
	BkBizId             int64  `json:"bk_biz_id" gorm:"column:bk_biz_id"`
	DbAppAbbr           string `json:"db_app_abbr" gorm:"column:db_app_abbr"`
	BkBizName           string `json:"bk_biz_name" gorm:"column:bk_biz_name"`
	ImmuteDomain        string `json:"immute_domain" gorm:"column:immute_domain"`
	Port                int    `json:"port" gorm:"column:port"`
	BkCloudId           int    `json:"bk_cloud_id" gorm:"column:bk_cloud_id"`
	ClusterId           int    `json:"cluster_id" gorm:"column:cluster_id"`
	DbLike              string `json:"dblike" gorm:"column:dblike"`
	TbLike              string `json:"tblike" gorm:"column:tblike"`
	PartitionColumn     string `json:"partition_columns" gorm:"column:partition_column"`
	PartitionColumnType string `json:"partition_column_type" gorm:"column:partition_column_type"`
	// 保留的分区个数 ReservedPartition := ExpireTime / PartitionTimeInterval
	ReservedPartition int `json:"reserved_partition" gorm:"column:reserved_partition"`
	ExtraPartition    int `json:"extra_partition" gorm:"column:extra_partition"`
	// 分区间隔
	PartitionTimeInterval int `json:"partition_time_interval" gorm:"column:partition_time_interval"`
	PartitionType         int `json:"partition_type" gorm:"column:partition_type"`
	// 数据过期天数
	ExpireTime int `json:"expire_time"`
	// 集群所在的时区
	TimeZone string `json:"time_zone"`
	// 分区规则启用或者禁用
	Phase      string    `json:"phase" gorm:"column:phase"`
	Creator    string    `json:"creator" gorm:"column:creator"`
	Updator    string    `json:"updator" gorm:"column:updator"`
	CreateTime time.Time `json:"create_time" gorm:"column:create_time"`
	UpdateTime time.Time `json:"update_time" gorm:"column:update_time"`
}

// PartitionConfigWithLog 分区配置以及执行日志
type PartitionConfigWithLog struct {
	PartitionConfig
	// 这里故意设置为string而不是time.Time，因为当值为null会被转换为1-01-01 08:00:00
	ExecuteTime string `json:"execute_time" gorm:"execute_time"`
	// 分区任务的状态
	Status string `json:"status" gorm:"status"`
	// 分区检查的结果
	CheckInfo string `json:"check_info" gorm:"check_info"`
}

// ConfigDetail 具体到库表的分区配置
type ConfigDetail struct {
	PartitionConfig
	DbName string `json:"dbname"`
	TbName string `json:"tbname"`
	// 是否已经分区
	Partitioned  bool `json:"partitioned"`
	HasUniqueKey bool `json:"has_unique_key"`
}

// Ticket 分区单据
type Ticket struct {
	BkBizId           int    `json:"bk_biz_id"`
	TicketType        string `json:"ticket_type"`
	Remark            string `json:"remark"`
	IgnoreDuplication bool   `json:"ignore_duplication"`
	Details           Detail `json:"details"`
	ImmuteDomain      string `json:"immute_domain"`
	CronDate          string `json:"cron_date"`
}

// Details 单据参数
type Details struct {
	Infos    []Info           `json:"infos"`
	Clusters ClustersResponse `json:"clusters"`
}

// Detail 用于创建单据
type Detail struct {
	Infos []Info `json:"infos"`
}

// Info 用于创建单据
type Info struct {
	BkCloudId int64  `json:"bk_cloud_id"`
	Ip        string `json:"ip"`
	FileName  string `json:"file_name"`
}

// ClustersResponse 用于创建单据
type ClustersResponse struct {
	ClusterResponse map[string]ClusterResponse `json:"cluster_response"`
}

// ClusterResponse 用于创建单据
type ClusterResponse struct {
	Id              int    `json:"id"`
	Creator         string `json:"creator"`
	Updater         string `json:"updater"`
	Name            string `json:"name"`
	Alias           string `json:"alias"`
	BkBizId         int    `json:"bk_biz_id"`
	ClusterType     string `json:"cluster_type"`
	DbModuleId      int    `json:"db_module_id"`
	ImmuteDomain    string `json:"immute_domain"`
	MajorVersion    string `json:"major_version"`
	Phase           string `json:"phase"`
	Status          string `json:"status"`
	BkCloudId       int    `json:"bk_cloud_id"`
	Region          string `json:"region"`
	TimeZone        string `json:"time_zone"`
	ClusterTypeName string `json:"cluster_type_name"`
}

// PartitionObject 待执行的分区语句集合
type PartitionObject struct {
	Ip             string         `json:"ip"`
	Port           int            `json:"port"`
	ShardName      string         `json:"shard_name"`
	ExecuteObjects []PartitionSql `json:"execute_objects"`
}

// ManageLogs 用于记录分区配置信息的变更
type ManageLogs struct {
	ID          int64     `gorm:"column:id;primary_key;auto_increment"`
	ConfigId    int       `gorm:"column:config_id"`
	BkBizId     int64     `gorm:"column:bk_biz_id"`
	Operate     string    `gorm:"column:operate"`
	Operator    string    `gorm:"column:operator"`
	Para        string    `gorm:"column:para"`
	ExecuteTime time.Time `gorm:"column:execute_time"`
}

// PartitionLogsParam TODO
type PartitionLogsParam struct {
	Para string
	Err  error
}
