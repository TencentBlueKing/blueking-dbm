package service

// Daily TODO
const Daily = "daily"

// Retry TODO
const Retry = "retry"

const Alarm = "alarm"

const Scheduler = "127.0.0.1"

// PartitionJob TODO
type PartitionJob struct {
	ClusterType string `json:"cluster_type"`
	CronType    string `json:"cron_type"`
	ZoneOffset  int    `json:"zone_offset"`
	ZoneName    string `json:"zone_name"`
	CronDate    string `json:"cron_date"`
	Hour        string `json:"hour"`
}

// TendbhaRelation tendbha机器与分区配置关系
type TendbhaRelation struct {
	Machine        string           `json:"machine"`
	ClusterConfigs []ClusterConfigs `json:"cluster_configs"`
}

// ClusterConfigs 集群信息与其分区配置
type ClusterConfigs struct {
	ClusterId int                `json:"cluster_id"`
	Master    Host               `json:"master"`
	Configs   []*PartitionConfig `json:"configs"`
}

// TendbClusterRelation tendbha集群信息与分区规则
type TendbClusterRelation struct {
	Cluster  []int      `json:"cluster"`
	Machines []string   `json:"machines"`
	Rules    []*Checker `json:"rules"`
}

// TendbhaRelationBiz 业务、机器与分区配置所属关系
type TendbhaRelationBiz struct {
	BkBizId   int64             `json:"bk_biz_id"`
	Relations []TendbhaRelation `json:"relations"`
}

// SpiderNode tendbcluster节点信息
type SpiderNode struct {
	Ip    string `json:"ip"`
	Port  int    `json:"port"`
	Cloud int    `json:"cloud"`
	// 分片编号
	SplitNum string `json:"split_num"`
	// spider实例类型 mysql or TDBCTL
	Wrapper    string `json:"wrapper"`
	ServerName string `json:"server_name"`
}

type CheckSummary struct {
	BkBizId   int    `json:"bk_biz_id" gorm:"column:bk_biz_id"`
	DbAppAbbr string `json:"db_app_abbr" gorm:"column:db_app_abbr"`
	Cnt       int    `json:"cnt" gorm:"column:cnt"`
	Ids       string `json:"ids" gorm:"column:ids"`
}
