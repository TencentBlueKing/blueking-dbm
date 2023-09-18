package service

const connLogDB = "infodba_schema"
const insertConnLogPriv = "grant insert on infodba_schema.conn_log to"
const setBinlogOff = "SET SESSION sql_log_bin=0;"
const setBinlogOn = "SET SESSION sql_log_bin=1;"
const setDdlByCtlOFF = "SET SESSION ddl_execute_by_ctl=off;"
const setTcAdminOFF = "SET SESSION tc_admin=off;"
const setDdlByCtlON = "SET SESSION ddl_execute_by_ctl=on;"
const flushPriv = "flush privileges;"
const sep string = "\n        "

// PrivTaskPara AddPrivDryRun,AddPriv 函数的入参
type PrivTaskPara struct {
	BkBizId int64 `json:"bk_biz_id"`
	// 单据要记录提单时的账号规则内容，执行时以提单时的账号规则执行
	ClusterType     string           `json:"cluster_type"`
	User            string           `json:"user"`
	Operator        string           `json:"operator"`
	AccoutRules     []TbAccountRules `json:"account_rules"`
	SourceIPs       []string         `json:"source_ips"`
	TargetInstances []string         `json:"target_instances"`
}

/*
// Instance GetClusterInfo 函数返回的结构体
type Instance struct {
	Proxies     []Proxy   `json:"proxies"`
	Storages    []Storage `json:"storages"`
	ClusterType string    `json:"cluster_type"`
	BkBizId     int64     `json:"bk_biz_id"`
	DbModuleId  int64     `json:"db_module_id"`
	BindTo      string    `json:"bind_to"`
	BkCloudId   int64     `json:"bk_cloud_id"`
}
*/

// Instance GetCluster 函数返回的结构体
type Instance struct {
	Proxies      []Proxy   `json:"proxies"`
	Storages     []Storage `json:"storages"`
	SpiderMaster []Proxy   `json:"spider_master"`
	SpiderSlave  []Proxy   `json:"spider_slave"`
	ClusterType  string    `json:"cluster_type"`
	BkBizId      int64     `json:"bk_biz_id"`
	DbModuleId   int64     `json:"db_module_id"`
	BindTo       string    `json:"bind_to"`
	EntryRole    string    `json:"entry_role"`
	BkCloudId    int64     `json:"bk_cloud_id"`
	ImmuteDomain string    `json:"immute_domain"`
}

// Cluster GetAllClustersInfo 函数返回 Cluster 数组
type Cluster struct {
	DbModuleId   int64     `json:"db_module_id"`
	BkBizId      string    `json:"bk_biz_id"`
	SpiderMaster []Proxy   `json:"spider_master"`
	SpiderSlave  []Proxy   `json:"spider_slave"`
	SpiderMnt    []Proxy   `json:"spider_mnt"`
	Proxies      []Proxy   `json:"proxies"`
	Storages     []Storage `json:"storages"`
	ClusterType  string    `json:"cluster_type"`
	ImmuteDomain string    `json:"immute_domain"`
	BkCloudId    int64     `json:"bk_cloud_id"`
}

// Proxy proxy 实例
type Proxy struct {
	IP        string `json:"ip"`
	Port      int64  `json:"port"`
	AdminPort int64  `json:"admin_port"`
	Status    string `json:"status"`
}

// Storage mysql 后端节点
type Storage struct {
	IP           string `json:"ip"`
	Port         int64  `json:"port"`
	InstanceRole string `json:"instance_role"`
	Status       string `json:"status"`
}

// Domain GetClusterInfo 函数的入参
type Domain struct {
	EntryName string `json:"entry_name" url:"entry_name"`
}

// BkBizId QueryAccountRule 函数的入参
type BkBizId struct {
	BkBizId     int64   `json:"bk_biz_id" url:"bk_biz_id"`
	ClusterType *string `json:"cluster_type" url:"cluster_type"`
}

// BkBizIdPara 业务 id，GetAllClustersInfo 函数的入参
type BkBizIdPara struct {
	BkBizId int64 `json:"bk_biz_id" url:"bk_biz_id"`
}

// AddPrivWithoutAccountRule 函数的入参
type AddPrivWithoutAccountRule struct {
	BkBizId    int64    `json:"bk_biz_id"`
	User       string   `json:"user"`
	Hosts      []string `json:"hosts"`
	Psw        string   `json:"psw"`
	Dbname     string   `json:"dbname"`
	Priv       string   `json:"priv"`
	DmlDdlPriv string   `json:"dml_ddl_priv"`
	GlobalPriv string   `json:"global_priv"`
	Operator   string   `json:"operator"`
	Address    string   `json:"address"`
	BkCloudId  *int64   `json:"bk_cloud_id"`
	Role       string   `json:"role"`
}
