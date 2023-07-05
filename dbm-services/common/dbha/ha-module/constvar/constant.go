package constvar

const (
	// Agent TODO
	Agent = "agent"
	// GM TODO
	GM = "gm"
	// GCM TODO
	GCM = "gcm"
	// GMM TODO
	GMM = "gmm"
	// GQA TODO
	GQA = "gqa"
	// GDM TODO
	GDM = "gdm"
)

const (
	// MySQLClusterType TODO
	MySQLClusterType = "tendbha"
	// MySQLMetaType TODO
	MySQLMetaType = "backend"
	// MySQLProxyMetaType TODO
	MySQLProxyMetaType = "proxy"
	// MySQL TODO
	MySQL = "tendbha:backend"
	// MySQLProxy TODO
	MySQLProxy = "tendbha:proxy"
	// MySQLMaster TODO
	MySQLMaster = "backend_master"
	// MySQLSlave TODO
	MySQLSlave = "backend_slave"
	// MySQLRepeater TODO
	MySQLRepeater = "backend_repeater"
	// RedisClusterType TODO
	RedisClusterType = "TwemproxyRedisInstance"
	// TendisplusClusterType TODO
	TendisplusClusterType = "PredixyTendisplusCluster"
	// RedisMetaType TODO
	RedisMetaType = "tendiscache"
	// PredixyMetaType TODO
	PredixyMetaType = "predixy"
	// TwemproxyMetaType TODO
	TwemproxyMetaType = "twemproxy"
	// TendisplusMetaType TODO
	TendisplusMetaType = "tendisplus"
	// TendisCache TODO
	TendisCache = "Rediscache"
	// Twemproxy TODO
	Twemproxy = "Twemproxy"
	// Predixy TODO
	Predixy = "Predixy"
	// Tendisplus TODO
	Tendisplus = "Tendisplus"
)

const (
	// AutoSwitch TODO
	AutoSwitch = "AutoSwitch"
	// HandSwitch TODO
	HandSwitch = "HandSwitch"
	// NoSwitch TODO
	NoSwitch = "NoSwitch"
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
// NB: Any adjustments need to be notified to the front-end development
const (
	CheckSwitchInfo = "info"
	CheckSwitchFail = "failed"
	SwitchInfo      = "info"
	SwitchSucc      = "success"
	SwitchFail      = "failed"
	UpdateMetaInfo  = "info"
	UpdateMetaFail  = "failed"

	SwitchInfoDoubleCheck = "info"
	SwitchInfoSlaveIp     = "slave_ip"
	SwitchInfoSlavePort   = "slave_port"
)

// checksum sql
const (
	// CheckSumSql checksum number
	CheckSumSql = "select count(distinct `db`, tbl) from infodba_schema.checksum where ts > date_sub(now(), interval 7 day)"
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
