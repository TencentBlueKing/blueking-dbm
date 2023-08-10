package service

import (
	"time"
)

// PartitionConfig 分区配置表
type PartitionConfig struct {
	ID                  int    `json:"id" gorm:"column:id;primary_key;auto_increment"`
	BkBizId             int    `json:"bk_biz_id" gorm:"column:bk_biz_id"`
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
	TicketId    int    `json:"ticket_id" gorm:"ticket_id"`
	// 分区任务的状态
	Status string `json:"status" gorm:"status"`
	// 分区单据的状态
	TicketStatus string `json:"ticket_status" gorm:"ticket_status"`
	// 分区检查的结果
	CheckInfo string `json:"check_info" gorm:"check_info"`
}

// ConfigDetail 具体到库表的分区配置
type ConfigDetail struct {
	PartitionConfig
	DbName string `json:"dbname"`
	TbName string `json:"tbname"`
	// 是否已经分区
	Partitioned bool `json:"partitioned"`
}

// Ticket 分区单据
type Ticket struct {
	BkBizId    int    `json:"bk_biz_id"`
	TicketType string `json:"ticket_type"`
	Remark     string `json:"remark"`
	Details    Detail `json:"details"`
}

// Details 单据参数
type Details struct {
	Infos    []Info           `json:"infos"`
	Clusters ClustersResponse `json:"clusters"`
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

// Detail 用于创建单据
type Detail struct {
	Infos []Info `json:"infos"`
}

// Info 用于创建单据
type Info struct {
	ConfigId         int               `json:"config_id"`
	ClusterId        int               `json:"cluster_id"`
	ImmuteDomain     string            `json:"immute_domain"`
	BkCloudId        int               `json:"bk_cloud_id"`
	PartitionObjects []PartitionObject `json:"partition_objects"`
}

// PartitionObject 待执行的分区语句集合
type PartitionObject struct {
	Ip             string         `json:"ip"`
	Port           int            `json:"port"`
	ShardName      string         `json:"shard_name"`
	ExecuteObjects []PartitionSql `json:"execute_objects"`
}
