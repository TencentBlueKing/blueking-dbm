package service

import "dbm-services/mysql/db-partition/util"

// MysqlPartitionConfig TODO
const MysqlPartitionConfig = "mysql_partition_config"

// SpiderPartitionConfig TODO
const SpiderPartitionConfig = "spider_partition_config"

// MysqlPartitionCronLogTable TODO
const MysqlPartitionCronLogTable = "mysql_partition_cron_log"

// SpiderPartitionCronLogTable TODO
const SpiderPartitionCronLogTable = "spider_partition_cron_log"
const online = "online"
const offline = "offline"
const extraTime = 15

// ExistRule TODO
type ExistRule struct {
	DbLike string `gorm:"column:dblike"`
	TbLike string `gorm:"column:tblike"`
}

// QueryParititionsInput TODO
type QueryParititionsInput struct {
	ClusterType   string   `json:"cluster_type"`
	BkBizId       int64    `json:"bk_biz_id"`
	Ids           []int64  `json:"ids"`
	ImmuteDomains []string `json:"immute_domains"`
	DbLikes       []string `json:"dblikes"`
	TbLikes       []string `json:"tblikes"`
	Limit         int      `json:"limit"`
	Offset        int      `json:"offset"`
}

// QueryLogInput TODO
type QueryLogInput struct {
	ClusterType string `json:"cluster_type"`
	ConfigId    int64  `json:"config_id"`
	Limit       int    `json:"limit"`
	Offset      int    `json:"offset"`
	StartTime   string `json:"start_time"`
	EndTime     string `json:"end_time"`
}

// CreatePartitionsInput TODO
type CreatePartitionsInput struct {
	BkBizId               int      `json:"bk_biz_id"`
	ClusterType           string   `json:"cluster_type"`
	ImmuteDomain          string   `json:"immute_domain"`
	Port                  int      `gorm:"column:port"`
	BkCloudId             int      `gorm:"column:bk_cloud_id"`
	ClusterId             int      `json:"cluster_id"`
	DbLikes               []string `json:"dblikes"`
	TbLikes               []string `json:"tblikes"`
	PartitionColumn       string   `json:"partition_column"`
	PartitionColumnType   string   `json:"partition_column_type"`
	ExpireTime            int      `json:"expire_time"`             // 分区过期时间
	PartitionTimeInterval int      `json:"partition_time_interval"` // 分区间隔
	TimeZone              string   `json:"time_zone"`
	Creator               string   `json:"creator"`
	Updator               string   `json:"updator"`
}

// DeletePartitionConfigByIds TODO
type DeletePartitionConfigByIds struct {
	ClusterType string  `json:"cluster_type"`
	BkBizId     int64   `json:"bk_biz_id"`
	Ids         []int64 `json:"ids"`
}

// DisablePartitionInput TODO
type DisablePartitionInput struct {
	ClusterType string  `json:"cluster_type"`
	Operator    string  `json:"operator"`
	Ids         []int64 `json:"ids"`
}

// EnablePartitionInput TODO
type EnablePartitionInput struct {
	ClusterType string  `json:"cluster_type"`
	Operator    string  `json:"operator"`
	Ids         []int64 `json:"ids"`
}

// ManageLog 审计分区管理行为
type ManageLog struct {
	Id       int64           `gorm:"column:id;primary_key;auto_increment" json:"id"`
	ConfigId int64           `gorm:"column:config_id;not_null" json:"config_id"`
	BkBizId  int64           `gorm:"column:bk_biz_id;not_null" json:"bk_biz_id"`
	Operator string          `gorm:"column:operator" json:"operator"`
	Para     string          `gorm:"column:para" json:"para"`
	Time     util.TimeFormat `gorm:"column:execute_time" json:"execute_time"`
}
