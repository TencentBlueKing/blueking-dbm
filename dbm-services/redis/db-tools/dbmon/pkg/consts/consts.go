// Package consts 常量
package consts

// version
const (
	BkDbmonVersion = "v0.12"
)

const (
	// TendisTypePredixyRedisCluster predixy + RedisCluster架构
	TendisTypePredixyRedisCluster = "PredixyRedisCluster"
	// TendisTypePredixyTendisplusCluster predixy + TendisplusCluster架构
	TendisTypePredixyTendisplusCluster = "PredixyTendisplusCluster"
	// TendisTypeTwemproxyRedisInstance twemproxy + RedisInstance架构
	TendisTypeTwemproxyRedisInstance = "TwemproxyRedisInstance"
	// TendisTypeTwemproxyTendisplusInstance twemproxy+ TendisplusInstance架构
	TendisTypeTwemproxyTendisplusInstance = "TwemproxyTendisplusInstance"
	// TendisTypeTwemproxyTendisSSDInstance twemproxy+ TendisSSDInstance架构
	TendisTypeTwemproxyTendisSSDInstance = "TwemproxyTendisSSDInstance"
	// TendisTypeRedisInstance RedisCache 主从版
	TendisTypeRedisInstance = "RedisInstance"
	// TendisTypeTendisplusInsance Tendisplus 主从版
	TendisTypeTendisplusInsance = "TendisplusInstance"
	// TendisTypeTendisSSDInsance TendisSSD 主从版
	TendisTypeTendisSSDInsance = "TendisSSDInstance"
	// TendisTypeRedisCluster 原生RedisCluster 架构
	TendisTypeRedisCluster = "RedisCluster"
	// TendisTypeTendisplusCluster TendisplusCluster架构
	TendisTypeTendisplusCluster = "TendisplusCluster"

	// MongoTypeShardedCluster TODO
	MongoTypeShardedCluster = "ShardedCluster"
	// MongoTypeReplicaSet TODO
	MongoTypeReplicaSet = "ReplicaSet"
	// MongoTypeStandalone TODO
	MongoTypeStandalone = "Standalone"
)

const (
	// RedisMasterRole redis role master
	RedisMasterRole = "master"
	// RedisSlaveRole redis role slave
	RedisSlaveRole = "slave"

	// RedisNoneRole none role
	RedisNoneRole = "none"

	// MasterLinkStatusUP up status
	MasterLinkStatusUP = "up"
	// MasterLinkStatusDown down status
	MasterLinkStatusDown = "down"

	// TendisSSDIncrSyncState IncrSync state
	TendisSSDIncrSyncState = "IncrSync"
	// TendisSSDReplFollowtate REPL_FOLLOW  state
	TendisSSDReplFollowtate = "REPL_FOLLOW"
)

const (
	// RedisLinkStateConnected redis connection status connected
	RedisLinkStateConnected = "connected"
	// RedisLinkStateDisconnected redis connection status disconnected
	RedisLinkStateDisconnected = "disconnected"
)

const (
	// NodeStatusPFail Node is in PFAIL state. Not reachable for the node you are contacting, but still logically reachable
	NodeStatusPFail = "fail?"
	// NodeStatusFail Node is in FAIL state. It was not reachable for multiple nodes that promoted the PFAIL state to FAIL
	NodeStatusFail = "fail"
	// NodeStatusHandshake Untrusted node, we are handshaking.
	NodeStatusHandshake = "handshake"
	// NodeStatusNoAddr No address known for this node
	NodeStatusNoAddr = "noaddr"
	// NodeStatusNoFlags no flags at all
	NodeStatusNoFlags = "noflags"
)

const (
	// ClusterStateOK command 'cluster info',cluster_state
	ClusterStateOK = "ok"
)
const (
	// DefaultMinSlots  0
	DefaultMinSlots = 0
	// DefaultMaxSlots 16383
	DefaultMaxSlots = 16383
)

// time layout
const (
	UnixtimeLayout     = "2006-01-02 15:04:05"
	FilenameTimeLayout = "20060102-150405"
	FilenameDayLayout  = "20060102"
)

// account
const (
	MysqlAaccount = "mysql"
	MysqlGroup    = "mysql"
)

// path dirs
const (
	UsrLocal            = "/usr/local"
	PackageSavePath     = "/data/install"
	Data1Path           = "/data1"
	DataPath            = "/data"
	DbaReportSaveDir    = "/home/mysql/dbareport/"
	BackupReportSaveDir = "/home/mysql/dbareport/"
	RedisReportSaveDir  = "/home/mysql/dbareport/redis/"
)

// tool path
const (
	DbToolsPath             = "/home/mysql/dbtools"
	RedisShakeBin           = "/home/mysql/dbtools/redis-shake"
	RedisSafeDeleteToolBin  = "/home/mysql/dbtools/redisSafeDeleteTool"
	LdbTendisplusBin        = "/home/mysql/dbtools/ldb_tendisplus"
	TredisverifyBin         = "/home/mysql/dbtools/tredisverify"
	TredisBinlogBin         = "/home/mysql/dbtools/tredisbinlog"
	TredisDumpBin           = "/home/mysql/dbtools/tredisdump"
	NetCatBin               = "/home/mysql/dbtools/netcat"
	TendisKeyLifecycleBin   = "/home/mysql/dbtools/tendis-key-lifecycle"
	ZkWatchBin              = "/home/mysql/dbtools/zkwatch"
	ZstdBin                 = "/home/mysql/dbtools/zstd"
	LzopBin                 = "/home/mysql/dbtools/lzop"
	LdbWithV38Bin           = "/home/mysql/dbtools/ldb_with_len.3.8"
	LdbWithV513Bin          = "/home/mysql/dbtools/ldb_with_len.5.13"
	MyRedisCaptureBin       = "/home/mysql/dbtools/myRedisCapture"
	BinlogToolTendisplusBin = "/home/mysql/dbtools/binlogtool_tendisplus"
	RedisCliBin             = "/home/mysql/dbtools/redis-cli"
)

// backup
const (
	NormalBackupType  = "normal_backup"
	ForeverBackupType = "forever_backup"
	IBSBackupClient   = "/usr/local/bin/backup_client"
	COSBackupClient   = "/usr/local/backup_client/bin/backup_client"

	RedisFullBackupTAG    = "REDIS_FULL"
	RedisBinlogTAG        = "REDIS_BINLOG"
	RedisForeverBackupTAG = "DBFILE"

	RedisFullBackupReportType   = "redis_fullbackup"
	RedisBinlogBackupReportType = "redis_binlogbackup"

	DoingRedisFullBackFileList = "redis_backup_file_list_%d_doing"
	DoneRedisFullBackFileList  = "redis_backup_file_list_%d_done"

	DoingRedisBinlogFileList = "redis_binlog_file_list_%d_doing"
	DoneRedisBinlogFileList  = "redis_binlog_file_list_%d_done"

	RedisFullbackupRepoter = "redis_fullbackup_%s.log"
	RedisBinlogRepoter     = "redis_binlog_%s.log"

	BackupStatusStart             = "start"
	BackupStatusRunning           = "running"
	BackupStatusToBakSystemStart  = "to_backup_system_start"
	BackupStatusToBakSystemFailed = "to_backup_system_failed"
	BackupStatusToBakSysSuccess   = "to_backup_system_success"
	BackupStatusFailed            = "failed"
	BackupStatusLocalSuccess      = "local_success"

	CacheBackupModeAof = "aof"
	CacheBackupModeRdb = "rdb"
)

const (
	// RedisHotKeyReporter TODO
	RedisHotKeyReporter = "redis_hotkey_%s.log"
	// RedisBigKeyReporter TODO
	RedisBigKeyReporter = "redis_bigkey_%s.log"
	// RedisKeyModeReporter TODO
	RedisKeyModeReporter = "redis_keymod_%s.log"
	// RedisKeyLifeReporter TODO
	RedisKeyLifeReporter = "redis_keylife_%s.log"
)

// meta role
const (
	MetaRoleRedisMaster = "redis_master"
	MetaRoleRedisSlave  = "redis_slave"
	MetaRolePredixy     = "predixy"
	MetaRoleTwemproxy   = "twemproxy"
)

const (
	// PayloadFormatRaw raw
	PayloadFormatRaw = "raw"
	// PayloadFormatBase64 base64
	PayloadFormatBase64 = "base64"
)

// IsClusterDbType 存储端是否是cluster类型
func IsClusterDbType(dbType string) bool {
	if dbType == TendisTypePredixyRedisCluster ||
		dbType == TendisTypePredixyTendisplusCluster ||
		dbType == TendisTypeRedisCluster ||
		dbType == TendisTypeTendisplusCluster {
		return true
	}
	return false
}

// IsRedisInstanceDbType 存储端是否是cache类型
func IsRedisInstanceDbType(dbType string) bool {
	if dbType == TendisTypePredixyRedisCluster ||
		dbType == TendisTypeTwemproxyRedisInstance ||
		dbType == TendisTypeRedisInstance ||
		dbType == TendisTypeRedisCluster {
		return true
	}
	return false
}

// IsTendisplusInstanceDbType 存储端是否是tendisplus类型
func IsTendisplusInstanceDbType(dbType string) bool {
	if dbType == TendisTypePredixyTendisplusCluster ||
		dbType == TendisTypeTwemproxyTendisplusInstance ||
		dbType == TendisTypeTendisplusInsance ||
		dbType == TendisTypeTendisplusCluster {
		return true
	}
	return false
}

// IsTendisSSDInstanceDbType 存储端是否是tendisSSD类型
func IsTendisSSDInstanceDbType(dbType string) bool {
	if dbType == TendisTypeTwemproxyTendisSSDInstance ||
		dbType == TendisTypeTendisSSDInsance {
		return true
	}
	return false
}

// IsRedisMetaRole TODO
func IsRedisMetaRole(metaRole string) bool {
	if metaRole == MetaRoleRedisMaster ||
		metaRole == MetaRoleRedisSlave {
		return true
	}
	return false
}

// IsMongo TODO
func IsMongo(clusterType string) bool {
	if clusterType == MongoTypeShardedCluster || clusterType == MongoTypeReplicaSet || clusterType == MongoTypeStandalone {
		return true
	}
	return false
}
