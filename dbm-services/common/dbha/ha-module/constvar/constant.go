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
	// LOG_DEBUG TODO
	LOG_DEBUG = "LOG_DEBUG"
	// LOG_INFO TODO
	LOG_INFO = "LOG_INFO"
	// LOG_WARN TODO
	LOG_WARN = "LOG_WARN"
	// LOG_ERROR TODO
	LOG_ERROR = "LOG_ERROR"
	// LOG_PANIC TODO
	LOG_PANIC = "LOG_PANIC"
	// LOG_FATAL TODO
	LOG_FATAL = "LOG_FATAL"

	// LOG_DEF_PATH TODO
	LOG_DEF_PATH = "./dbha.log"
	// LOG_DEF_BACKUPS TODO
	LOG_DEF_BACKUPS = 5
	// LOG_DEF_AGE TODO
	LOG_DEF_AGE = 30
	// LOG_DEF_SIZE TODO
	LOG_DEF_SIZE = 1024
	// LOG_MIN_SIZE TODO
	LOG_MIN_SIZE = 1
)

const (
	// REDIS_MAX_DIE_TIME TODO
	REDIS_MAX_DIE_TIME = 600
	// REDIS_DEF_AUTH TODO
	REDIS_DEF_AUTH = "tendis+test"
)

const (
	// REDIS_PASSWORD_LACK TODO
	REDIS_PASSWORD_LACK = "NOAUTH Authentication required"
	// REDIS_PASSWORD_INVALID TODO
	REDIS_PASSWORD_INVALID = "invalid password"
	// PREDIXY_PASSWORD_LACK TODO
	PREDIXY_PASSWORD_LACK = "auth permission deny"

	// SSH_PASSWORD_LACK_OR_INVALID TODO
	SSH_PASSWORD_LACK_OR_INVALID = "unable to authenticate"
)

const (
	// DBHA_EVENT_NAME TODO
	DBHA_EVENT_NAME = "dbha_event"
	// DBHA_EVENT_REDIS_SWITCH_SUCC TODO
	DBHA_EVENT_REDIS_SWITCH_SUCC = "dbha_redis_switch_succ"
	// DBHA_EVENT_REDIS_SWITCH_ERR TODO
	DBHA_EVENT_REDIS_SWITCH_ERR = "dbha_redis_switch_err"
	// DBHA_EVENT_MYSQL_SWITCH_SUCC TODO
	DBHA_EVENT_MYSQL_SWITCH_SUCC = "dbha_mysql_switch_ok"
	// DBHA_EVENT_MYSQL_SWITCH_ERR TODO
	DBHA_EVENT_MYSQL_SWITCH_ERR = "dbha_mysql_switch_err"
	// DBHA_EVENT_DETECT_AUTH TODO
	DBHA_EVENT_DETECT_AUTH = "dbha_detect_auth_fail"
	// DBHA_EVENT_DETECT_SSH TODO
	DBHA_EVENT_DETECT_SSH = "dbha_detect_ssh_fail"
	// DBHA_EVENT_DETECT_DB TODO
	DBHA_EVENT_DETECT_DB = "dbha_detect_db_fail"
	// DBHA_EVENT_DOUBLE_CHECK_SSH TODO
	DBHA_EVENT_DOUBLE_CHECK_SSH = "dbha_doublecheck_ssh_fail"
	// DBHA_EVENT_DOUBLE_CHECK_AUTH TODO
	DBHA_EVENT_DOUBLE_CHECK_AUTH = "dbha_doublecheck_auth_fail"
	// DBHA_EVENT_SYSTEM TODO
	DBHA_EVENT_SYSTEM = "dbha_system"

	// MONITOR_INFO_SWITCH TODO
	MONITOR_INFO_SWITCH = 0
	// MONITOR_INFO_DETECT TODO
	MONITOR_INFO_DETECT = 1
	// MONITOR_INFO_SYSTEM TODO
	MONITOR_INFO_SYSTEM = 2

	// MonitorReportType TODO
	MonitorReportType = "agent"
	// MonitorMessageKind TODO
	MonitorMessageKind = "event"
)

// status in switch_logs(result field)
// NB: Any adjustments need to be notified to the front-end development
const (
	CHECK_SWITCH_INFO = "info"
	CHECK_SWITCH_FAIL = "failed"
	SWITCH_INFO       = "info"
	SWITCH_SUCC       = "success"
	SWITCH_FAIL       = "failed"
	UPDATEMETA_INFO   = "info"
	UPDATEMETA_FAIL   = "failed"

	SWITCH_INFO_DOUBLECHECK = "info"
	SWITCH_INFO_SLAVE_IP    = "slave_ip"
	SWITCH_INFO_SLAVE_PORT  = "slave_port"
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
	TZ_UTC = "UTC"
	TZ_CST = "CST"
)
