package service

// MysqlPartitionConfig TODO
const MysqlPartitionConfig = "mysql_partition_config"

// SpiderPartitionConfig TODO
const SpiderPartitionConfig = "spider_partition_config"

// MysqlPartitionCronLogTable TODO
const MysqlPartitionCronLogTable = "mysql_partition_cron_log"

// SpiderPartitionCronLogTable TODO
const SpiderPartitionCronLogTable = "spider_partition_cron_log"

// MysqlPartition TODO
const MysqlPartition = "MYSQL_PARTITION"

// SpiderPartition TODO
const SpiderPartition = "SPIDER_PARTITION"
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
