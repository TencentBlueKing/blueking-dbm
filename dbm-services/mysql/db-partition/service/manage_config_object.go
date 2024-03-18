package service

import "time"

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
const offlinewithclu = "offlinewithclu"
const extraTime = 15

// MysqlManageLogsTable TODO
const MysqlManageLogsTable = "mysql_manage_logs"

// SpiderManageLogsTable TODO
const SpiderManageLogsTable = "spider_manage_logs"

// MysqlPartitionConfigScr TODO
const MysqlPartitionConfigScr = "mysql_partition_conf"

// SpiderPartitionConfigScr TODO
const SpiderPartitionConfigScr = "spider_partition_conf"

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
	BkBizId               int64    `json:"bk_biz_id"`    // 业务代号
	ClusterType           string   `json:"cluster_type"` // 集群类型
	ImmuteDomain          string   `json:"immute_domain"`
	Port                  int      `gorm:"column:port"`
	BkCloudId             int      `gorm:"column:bk_cloud_id"`
	ClusterId             int      `json:"cluster_id"` // 集群id 上架集群后，会有唯一id对应
	DbLikes               []string `json:"dblikes"`
	TbLikes               []string `json:"tblikes"`
	PartitionColumn       string   `json:"partition_column"`
	PartitionColumnType   string   `json:"partition_column_type"`
	ExpireTime            int      `json:"expire_time"`             // 分区过期时间
	PartitionTimeInterval int      `json:"partition_time_interval"` // 分区间隔
	TimeZone              string   `json:"time_zone"`
	Creator               string   `json:"creator"`
	Updator               string   `json:"updator"`
	RemoteHashAlgorithm   string   `json:"remote_hash_algorithm"`
}

// DeletePartitionConfigByIds TODO
type DeletePartitionConfigByIds struct {
	ClusterType string `json:"cluster_type"`
	BkBizId     int64  `json:"bk_biz_id"`
	Operator    string `json:"operator"`
	Ids         []int  `json:"ids"`
}

// DeletePartitionConfigByClusterIds TODO
type DeletePartitionConfigByClusterIds struct {
	ClusterType string `json:"cluster_type"`
	BkBizId     int64  `json:"bk_biz_id"`
	Operator    string `json:"operator"`
	ClusterIds  []int  `json:"cluster_ids"`
}

// DisablePartitionInput TODO
type DisablePartitionInput struct {
	ClusterType string `json:"cluster_type"`
	Operator    string `json:"operator"`
	Ids         []int  `json:"ids"`
	ClusterIds  []int  `json:"cluster_ids"`
}

// EnablePartitionInput TODO
type EnablePartitionInput struct {
	ClusterType string `json:"cluster_type"`
	Operator    string `json:"operator"`
	Ids         []int  `json:"ids"`
	ClusterIds  []int  `json:"cluster_ids"`
}

// ManageLog 审计分区管理行为
// 暂时未用，分区配置信息修改记录在mysql_manage_logs与spider_manage_logs
type ManageLog struct {
	Id       int64     `gorm:"column:id;primary_key;auto_increment" json:"id"`
	ConfigId int64     `gorm:"column:config_id;not_null" json:"config_id"`
	BkBizId  int64     `gorm:"column:bk_biz_id;not_null" json:"bk_biz_id"`
	Operator string    `gorm:"column:operator" json:"operator"`
	Para     string    `gorm:"column:para" json:"para"`
	Time     time.Time `gorm:"column:execute_time" json:"execute_time"`
}
