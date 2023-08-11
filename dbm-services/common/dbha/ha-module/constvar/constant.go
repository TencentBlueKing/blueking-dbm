package constvar

const (
	// Agent component name
	Agent = "agent"
	// GM component name
	GM = "gm"
	// GCM component name
	GCM = "gcm"
	// GMM component name
	GMM = "gmm"
	// GQA component name
	GQA = "gqa"
	// GDM component name
	GDM = "gdm"
)

//cluster type in cmdb
const (
	// TenDBHA cluster with proxy, mysql component
	TenDBHA = "tendbha"
	// TenDBCluster cluster with spider, mysql component
	TenDBCluster = "tendbcluster"
	// RedisCluster cluster with twemproxy component
	RedisCluster = "TwemproxyRedisInstance"
	// TendisplusCluster cluster with predixy component
	TendisplusCluster = "PredixyTendisplusCluster"
)

// instance type name in cmdb
const (
	//TenDBStorageType storage type name in tendbha
	TenDBStorageType = "backend"
	//TenDBProxyType proxy type name in tendbha
	TenDBProxyType = "proxy"

	//TenDBClusterStorageType storage type name in tendbcluster
	TenDBClusterStorageType = "remote"
	//TenDBClusterProxyType proxy type name in tendbcluster
	TenDBClusterProxyType = "spider"

	// RedisMetaType storage layer type name in rediscluster
	RedisMetaType = "tendiscache"
	// TwemproxyMetaType proxy layer type name RedisCluster
	TwemproxyMetaType = "twemproxy"

	// PredixyMetaType proxy layer type name in  TendisplusCluster
	PredixyMetaType = "predixy"
	// TendisplusMetaType storage layer type name in TendisplusCluster
	TendisplusMetaType = "tendisplus"
)

//instance role in cmdb
const (
	// TenDBStorageMaster tendbha backend master role
	TenDBStorageMaster = "backend_master"
	// TenDBStorageSlave tendbha backend slave role
	TenDBStorageSlave = "backend_slave"
	// TenDBStorageRepeater tendbha backend repeater role
	TenDBStorageRepeater = "backend_repeater"

	// TenDBClusterStorageMaster tendbcluster remote master role
	TenDBClusterStorageMaster = "remote_master"
	// TenDBClusterStorageSlave tendbcluster remoteslave role
	TenDBClusterStorageSlave = "remote_slave"
	// TenDBClusterProxyMaster tendbcluster remote master role
	TenDBClusterProxyMaster = "spider_master"
	// TenDBClusterProxySlave tendbcluster remoteslave role
	TenDBClusterProxySlave = "spider_slave"
)

//detect type in config.yaml
const (
	// DetectTenDBHA detect TenDBHA
	DetectTenDBHA = "tendbha"
	// DetectTenDBCluster detect TenDBCluster
	DetectTenDBCluster = "tendbcluster"

	//TendisCache if specified, agent detect would detect RedisCluster's cache
	TendisCache = "Rediscache"
	//Twemproxy if specified, agent detect would detect RedisCluster's proxy
	Twemproxy = "Twemproxy"

	//Predixy if specified, agent detect would detect TendisplusCluster's proxy layer
	Predixy = "Predixy"
	//Tendisplus if specified, agent detect would detect TendisplusCluster's storage layer
	Tendisplus = "Tendisplus"
	// Riak TODO
	Riak = "riak"
)

//wrapper name in TenDBCluster
//Anytime compare should ignore case
const (
	WrapperSpiderMaster = "SPIDER"
	WrapperSpiderSlave  = "SPIDER_SLAVE"
	WrapperTdbctl       = "TDBCTL"
	WrapperMySQLMaster  = "mysql"
	WrapperMySQLSlave   = "mysql_slave"
)
const (
	// DBCheckSuccess TODO
	DBCheckSuccess = "DB_check_success"
	// DBCheckFailed TODO
	DBCheckFailed = "DB_check_failed"
	// SSHCheckFailed TODO
	SSHCheckFailed = "SSH_check_failed"
	// SSHCheckSuccess TODO
	SSHCheckSuccess = "SSH_check_success"
	// AUTHCheckFailed TODO
	AUTHCheckFailed = "AUTH_check_failed"
)

const (
	// RUNNING TODO
	RUNNING = "running"
	// UNAVAILABLE TODO
	UNAVAILABLE = "unavailable"
	// AVAILABLE TODO
	AVAILABLE = "available"
)

const (
	// AgentGetGMInfo TODO
	AgentGetGMInfo = "agent_get_GM_info"
	// UpdateInstanceStatus TODO
	UpdateInstanceStatus = "update_instance_status"
	// InsertInstanceStatus TODO
	InsertInstanceStatus = "insert_instance_status"
	// ReporterHALog TODO
	ReporterHALog = "reporter_log"
	// RegisterDBHAInfo TODO
	RegisterDBHAInfo = "register_dbha_info"
	// GetAliveAgentInfo TODO
	GetAliveAgentInfo = "get_alive_agent_info"
	// GetAliveGMInfo TODO
	GetAliveGMInfo = "get_alive_gm_info"
	// ReporterAgentHeartbeat TODO
	ReporterAgentHeartbeat = "reporter_agent_heartbeat"
	// ReporterGMHeartbeat TODO
	ReporterGMHeartbeat = "reporter_gm_heartbeat"
	// QuerySingleTotal TODO
	QuerySingleTotal = "query_single_total"
	// QueryIntervalTotal TODO
	QueryIntervalTotal = "query_interval_total"
	// QuerySingleIDC TODO
	QuerySingleIDC = "query_single_idc"
	// UpdateTimeDelay TODO
	UpdateTimeDelay = "update_time_delay"
	// InsertSwitchQueue TODO
	InsertSwitchQueue = "insert_switch_queue"
	// QuerySlaveCheckConfig TODO
	QuerySlaveCheckConfig = "query_slave_check_config"
	// UpdateSwitchQueue TODO
	UpdateSwitchQueue = "update_switch_queue"
	// InsertSwitchLog TODO
	InsertSwitchLog = "insert_switch_log"

	// HaStatusUrl TODO
	HaStatusUrl = "hastatus/"
	// DbStatusUrl TODO
	DbStatusUrl = "dbstatus/"
	// HaLogsUrl TODO
	HaLogsUrl = "halogs/"
	// SwitchQueueUrl TODO
	SwitchQueueUrl = "switchqueue/"
	// SwitchLogUrl TODO
	SwitchLogUrl = "switchlogs/"
)

const (
	// CmDBCityUrl TODO
	CmDBCityUrl = "dbmeta/dbha/cities/"
	// CmDBInstanceUrl TODO
	CmDBInstanceUrl = "dbmeta/dbha/instances/"
	// CmDBSwapRoleUrl TODO
	CmDBSwapRoleUrl = "dbmeta/dbha/swap_role/"
	// CmDBUpdateStatusUrl TODO
	CmDBUpdateStatusUrl = "dbmeta/dbha/update_status/"
	// GetDomainInfoUrl TODO
	GetDomainInfoUrl = "dns/domain/get/"
	// DeleteDomainUrl TODO
	DeleteDomainUrl = "dns/domain/delete/"
	// CmDBRedisSwapUrl TODO
	CmDBRedisSwapUrl = "dbmeta/dbha/tendis_cluster_swap/"
	// CmDBEntryDetailUrl TODO
	CmDBEntryDetailUrl = "dbmeta/dbha/entry_detail/"
	// CLBDeRegisterUrl TODO
	CLBDeRegisterUrl = "clb_deregister_part_target/"
	// CLBGetTargetsUrl TODO
	CLBGetTargetsUrl = "clb_get_target_private_ips/"
	// PolarisTargetsUrl TODO
	PolarisTargetsUrl = "polaris_describe_targets/"
	// PolarisUnBindUrl TODO
	PolarisUnBindUrl = "polaris_unbind_part_targets/"
	// BKConfigBatchUrl TODO
	BKConfigBatchUrl = "bkconfig/v1/confitem/batchget/"
	// BKConfigQueryUrl TODO
	BKConfigQueryUrl = "bkconfig/v1/confitem/query/"
)

//name service's type
const (
	EntryDns     = "dns"
	EntryPolaris = "polaris"
	EntryClb     = "clb"
)

const (
	// CmDBName TODO
	CmDBName = "cmdb"
	// HaDBName TODO
	HaDBName = "hadb"
	// DnsName TODO
	DnsName = "dns"
	// ApiGWName TODO
	ApiGWName = "apigw"
	// DBConfigName TODO
	DBConfigName = "db_config"

	// BkApiAuthorization TODO
	BkApiAuthorization = "x-bkapi-authorization"
	// BkToken TODO
	BkToken = "bk_token"

	// ConfMysqlFile TODO
	ConfMysqlFile = "mysql#user"
	// ConfMysqlType TODO
	ConfMysqlType = "init_user"
	// ConfMysqlNamespace TODO
	ConfMysqlNamespace = "tendb"
	// ConfMysqlName TODO
	ConfMysqlName = "os_mysql_pwd,os_mysql_user"

	// ConfOSFile TODO
	ConfOSFile = "os"
	// ConfOSType TODO
	ConfOSType = "osconf"
	// ConfCommon TODO
	ConfCommon = "common"
	// ConfOSPlat TODO
	ConfOSPlat = "plat"
	// ConfOSApp TODO
	ConfOSApp = "app"
	// ConfUserPasswd TODO
	ConfUserPasswd = "user_pwd"
)

const (
	// LogDebug TODO
	LogDebug = "LOG_DEBUG"
	// LogInfo TODO
	LogInfo = "LOG_INFO"
	// LogWarn TODO
	LogWarn = "LOG_WARN"
	// LogError TODO
	LogError = "LOG_ERROR"
	// LogPanic TODO
	LogPanic = "LOG_PANIC"
	// LogFatal TODO
	LogFatal = "LOG_FATAL"

	// LogDefPath TODO
	LogDefPath = "./dbha.log"
	// LogDefBackups TODO
	LogDefBackups = 5
	// LogDefAge TODO
	LogDefAge = 30
	// LogDefSize TODO
	LogDefSize = 1024
	// LogMinSize TODO
	LogMinSize = 1
)

const (
	// RedisMaxDieTime TODO
	RedisMaxDieTime = 600
	// RedisDefAuth TODO
	RedisDefAuth = "tendis+test"
)

const (
	// RedisPasswordLack TODO
	RedisPasswordLack = "NOAUTH Authentication required"
	// RedisPasswordInvalid TODO
	RedisPasswordInvalid = "invalid password"
	// PredixyPasswordLack TODO
	PredixyPasswordLack = "auth permission deny"

	// SSHPasswordLackORInvalid TODO
	SSHPasswordLackORInvalid = "unable to authenticate"
)

const (
	// DBHAEventName TODO
	DBHAEventName = "dbha_event"
	// DBHAEventRedisSwitchSucc TODO
	DBHAEventRedisSwitchSucc = "dbha_redis_switch_succ"
	// DBHAEventRedisSwitchErr TODO
	DBHAEventRedisSwitchErr = "dbha_redis_switch_err"
	// DBHAEventMysqlSwitchSucc TODO
	DBHAEventMysqlSwitchSucc = "dbha_mysql_switch_ok"
	// DBHAEventMysqlSwitchErr TODO
	DBHAEventMysqlSwitchErr = "dbha_mysql_switch_err"
	// DBHAEventMysqlSwitchSucc TODO
	DBHAEventRiakSwitchSucc = "dbha_riak_switch_ok"
	// DBHAEventMysqlSwitchErr TODO
	DBHAEventRiakSwitchErr = "dbha_riak_switch_err"
	// DBHAEventDetectAuth TODO
	DBHAEventDetectAuth = "dbha_detect_auth_fail"
	// DBHAEventDetectSSH TODO
	DBHAEventDetectSSH = "dbha_detect_ssh_fail"
	// DBHAEventDetectDB TODO
	DBHAEventDetectDB = "dbha_detect_db_fail"
	// DBHAEventDoubleCheckSSH TODO
	DBHAEventDoubleCheckSSH = "dbha_doublecheck_ssh_fail"
	// DBHAEventDoubleCheckAuth TODO
	DBHAEventDoubleCheckAuth = "dbha_doublecheck_auth_fail"
	// DBHAEventSystem TODO
	DBHAEventSystem = "dbha_system"

	// MonitorInfoSwitch TODO
	MonitorInfoSwitch = 0
	// MonitorInfoDetect TODO
	MonitorInfoDetect = 1
	// MonitorInfoSystem TODO
	MonitorInfoSystem = 2

	// MonitorReportType TODO
	MonitorReportType = "agent"
	// MonitorMessageKind TODO
	MonitorMessageKind = "event"
)

// status in switch_logs(result field)
// NB: Any adjustments need to be notified to the front-end developer 
const (
	InfoResult    = "info"
	FailResult    = "failed"
	SuccessResult = "success"
)

// status in tb_mon_switch_queue(status field)
const (
	SwitchStart   = "doing"
	SwitchFailed  = "failed"
	SwitchSuccess = "success"
)

//gcm use blow switch key to set/get switch instance info
//more detail refer to DataBaseSwitch.SetInfo/DataBaseSwitch.GetInfo
const (
	// DoubleCheckInfoKey gqa use to set double check info(gmm generated)
	DoubleCheckInfoKey = "dc_info"
	// DoubleCheckTimeKey gqa use to set double check time(gmm generated)
	DoubleCheckTimeKey = "dc_time"
	// SlaveIpKey use to set slave ip
	SlaveIpKey = "slave_ip"
	// SlavePortKey use to set slave port
	SlavePortKey = "slave_port"
)

// checksum sql
const (
	// CheckSumSql checksum number
	CheckSumSql = "select count(distinct `db`, tbl) from infodba_schema.checksum where ts > date_sub(now(), " +
		"interval 7 day)"
	// CheckSumFailSql inconsistent checksum number
	CheckSumFailSql = "select count(distinct `db`, tbl,chunk) from infodba_schema.checksum where " +
		"(this_crc <> master_crc or this_cnt <> master_cnt) and ts > date_sub(now(), interval 7 day)"
	// CheckDelaySql master and slave's time delay
	CheckDelaySql = "select unix_timestamp(now())-unix_timestamp(master_time) as time_delay, delay_sec as slave_delay " +
		"from infodba_schema.master_slave_heartbeat where master_server_id = ? and slave_server_id != master_server_id"
)

// timezone
const (
	TZUTC = "UTC"
	TZCST = "CST"
)

const (
	// DefaultDatabase default database info mysql instance
	DefaultDatabase = "infodba_schema"
)

const (
	RiakHttpPort = 8098
)
