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

	// MONITOR global monitor
	MONITOR = "monitor"
)

// cluster type in cmdb
const (
	// TenDBHA cluster with proxy, mysql component
	TenDBHA = "tendbha"
	// TenDBCluster cluster with spider, mysql component
	TenDBCluster = "tendbcluster"
	// RedisInstance ("RedisInstance", "RedisCache主从版"),
	RedisInstance = "RedisInstance"
	// PredixyRedisCluster EnumField("PredixyRedisCluster", _("Redis集群"))
	PredixyRedisCluster = "PredixyRedisCluster"
	// RedisCluster cluster with twemproxy component
	RedisCluster = "TwemproxyRedisInstance"
	// TendisplusCluster cluster with predixy component
	TendisplusCluster = "PredixyTendisplusCluster"
	// TendisSSDCluster cluster with tendisssd component
	TendisSSDCluster = "TwemproxyTendisSSDInstance"
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
	// TendisSSDMetaType tendisssd lay type name in TwemproxyTendisSSDInstance
	TendisSSDMetaType = "tendisssd"

	// PredixyMetaType proxy layer type name in  TendisplusCluster
	PredixyMetaType = "predixy"
	// TendisplusMetaType storage layer type name in TendisplusCluster
	TendisplusMetaType = "tendisplus"
	// SqlserverMetatype storage layer type name in SqlserverHa
	SqlserverMetatype = "sqlserver_ha"

	// Mongos MONGOS = EnumField("mongos", _("mongos"))  # mongos
	Mongos = "mongos"
)

// instance role in cmdb
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

// detect cluster type in config.yaml
const (
	// DetectTenDBHA detect TenDBHA
	DetectTenDBHA = "tendbha"
	// DetectTenDBCluster detect TenDBCluster
	DetectTenDBCluster = "tendbcluster"

	// DetectRedisInstance ("RedisInstance", "RedisCache主从版"),
	DetectRedisInstance = "RedisInstance"
	// DetectPredixyRedisCluster EnumField("PredixyRedisCluster", _("Redis集群"))
	DetectPredixyRedisCluster = "PredixyRedisCluster"
	// DetectTendisCache detect tendiscache and twemproxy
	DetectTendisCache = "TwemproxyRedisInstance"
	// DetectTendisplus detect tendisplus and predixy
	DetectTendisplus = "PredixyTendisplusCluster"
	// DetectTendisSSD detect tendisssd and twemproxy
	DetectTendisSSD = "TwemproxyTendisSSDInstance"

	//Predixy if specified, agent detect would detect TendisplusCluster's proxy layer
	Predixy = "Predixy"
	//Tendisplus if specified, agent detect would detect TendisplusCluster's storage layer
	Tendisplus = "Tendisplus"
	// Riak TODO
	Riak = "riak"
	// SqlserverHA TODO
	SqlserverHA = "sqlserver_ha"

	// MongoShardedCluster = EnumField("MongoShardedCluster", _("Mongo分片集群"))
	MongoShardCluster = "MongoShardedCluster"
)

// wrapper name in TenDBCluster
// Anytime compare should ignore case
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
	// SSHAuthFailed ssh auth failed
	SSHAuthFailed = "SSH_auth_failed"
	// RedisAuthFailed TODO
	RedisAuthFailed = "Redis_auth_failed"
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
	//GetInstanceStatus get detect info from ha_agent_logs
	GetInstanceStatus = "get_instance_status"
	// UpdateInstanceStatus TODO
	UpdateInstanceStatus = "update_instance_status"
	// InsertInstanceStatus TODO
	InsertInstanceStatus = "insert_instance_status"
	// ReporterHALog TODO
	ReporterHALog = "reporter_log"
	// RegisterDBHAInfo TODO
	RegisterDBHAInfo = "register_dbha_info"
	// GetAliveHAInfo TODO
	GetAliveHAInfo = "get_alive_ha_info"
	// GetAliveAgentInfo TODO
	GetAliveAgentInfo = "get_alive_agent_info"
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
	// ShieldConfigUrl api route to request ha_shield_config table
	ShieldConfigUrl = "shieldconfig/"
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
	//CmDBMigrateDumper migrate dumper from master to slave
	CmDBMigrateDumper = "dumper/switch/"
	// GetDomainInfoUrl TODO
	GetDomainInfoUrl = "dns/domain/get/"
	// DeleteDomainUrl TODO
	DeleteDomainUrl = "dns/domain/delete/"
	// UpdateDomainUrl TODO
	CreateDomainUrl = "dns/domain/put/"
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
	// BKPasswdQueryUrl TODO
	BKPasswdQueryUrl = "dbpriv/proxy_password/"
	//CmDBSqlserverSwapRoleUrl TODO
	CmDBSqlserverSwapRoleUrl = "dbmeta/dbha/sqlserver_cluster_swap/"
)

// name service's type
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

	// password server component
	ComponentRedis           = "redis"
	ComponentRedisProxy      = "redis_proxy"
	ComponentRedisProxyAdmin = "redis_proxy_admin"
	// password server user
	UserRedisDefault   = "default"
	UserMachineDefault = "mysql"
	// machine password instance
	MachineInstanceDefault = "0.0.0.0"
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
	RedisPasswordLack = "NOAUTH Authentication"
	// RedisPasswordInvalid TODO
	RedisPasswordInvalid = "invalid password"

	// RedisPasswordInvalid2 TODO
	RedisPasswordInvalid2 = "WRONGPASS invalid"

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
	// DBHAEventDetectRedisAuth TODO
	DBHAEventDetectRedisAuth = "dbha_detect_redis_auth_fail"
	// DBHAEventDetectSSHAuth TODO
	DBHAEventDetectSSHAuth = "dbha_detect_ssh_auth_fail"
	// DBHAEventDetectSSH TODO
	DBHAEventDetectSSH = "dbha_detect_ssh_fail"
	// DBHAEventDetectDB TODO
	DBHAEventDetectDB = "dbha_detect_db_fail"
	// DBHAEventDoubleCheckSSH TODO
	DBHAEventDoubleCheckSSH = "dbha_doublecheck_ssh_fail"
	// DBHAEventDoubleCheckAuth TODO
	DBHAEventDoubleCheckAuth = "dbha_doublecheck_auth_fail"
	// DBHAEventGlobalMonitor TODO
	DBHAEventGlobalMonitor = "dbha_global_monitor"

	// MonitorInfoSwitch TODO
	MonitorInfoSwitch = 0
	// MonitorInfoDetect TODO
	MonitorInfoDetect = 1
	// MonitorInfoGlobal global monitor for component work normal
	MonitorInfoGlobal = 2

	// MonitorReportType TODO
	MonitorReportType = "agent"
	// MonitorMessageKind TODO
	MonitorMessageKind = "event"
)

// status in switch_logs(result field)
// NB: Any adjustments need to be notified to the front-end developer
const (
	InfoResult    = "info"
	WarnResult    = "warn"
	FailResult    = "failed"
	SuccessResult = "success"
)

// status in ha_switch_queue(status field)
const (
	SwitchStart   = "doing"
	SwitchFailed  = "failed"
	SwitchSuccess = "success"
)

// gcm use blow switch key to set/get switch instance info
// more detail refer to DataBaseSwitch.SetInfo/DataBaseSwitch.GetInfo
const (
	// DoubleCheckInfoKey gqa use to set double check info(gmm generated)
	DoubleCheckInfoKey = "dc_info"
	// DoubleCheckTimeKey gqa use to set double check time(gmm generated)
	DoubleCheckTimeKey = "dc_time"
	// SlaveIpKey use to set slave ip
	SlaveIpKey = "slave_ip"
	// SlavePortKey use to set slave port
	SlavePortKey = "slave_port"
	//NewMasterBinlogFile consistent switch binlog file
	NewMasterBinlogFile = "new_master_binlog_file"
	//NewMasterBinlogPos consistent switch binlog pos
	NewMasterBinlogPos = "new_master_binlog_pos"
	//NewMasterHost new master's host
	NewMasterHost = "new_master_host"
	//NewMasterPort new master's port
	NewMasterPort = "new_master_port"
)

// checksum sql
const (
	// CheckSumSql checksum number
	CheckSumSql = "SELECT COUNT(DISTINCT `db`, tbl) AS total_count FROM (SELECT `db`, tbl FROM " +
		"infodba_schema.checksum WHERE ts > DATE_SUB(NOW(), INTERVAL 7 DAY) UNION SELECT `db`, tbl FROM " +
		"infodba_schema.checksum_history WHERE ts > DATE_SUB(NOW(), INTERVAL 7 DAY)) AS combined_results"

	// CheckSumFailSql inconsistent checksum number
	CheckSumFailSql = "SELECT COUNT(DISTINCT `db`, tbl, chunk) AS total_count FROM infodba_schema.checksum " +
		"WHERE (this_crc <> master_crc OR this_cnt <> master_cnt) AND ts > DATE_SUB(NOW(), INTERVAL 7 DAY) " +
		"UNION SELECT COUNT(DISTINCT `db`, tbl, chunk) AS total_count FROM infodba_schema.checksum_history " +
		"WHERE (this_crc <> master_crc OR this_cnt <> master_cnt) AND ts > DATE_SUB(NOW(), INTERVAL 7 DAY)"
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
