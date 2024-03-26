// Package consts 常量
package consts

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
)

// kibis of bits
const (
	Byte = 1 << (iota * 10)
	KiByte
	MiByte
	GiByte
	TiByte
	EiByte
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
	OSAccount     = "mysql"
	OSGroup       = "mysql"
)

// path dirs
const (
	UsrLocal           = "/usr/local"
	PackageCachePath   = "/data/dbbak"
	PackageSavePath    = "/data/install"
	Data1Path          = "/data1"
	DataPath           = "/data"
	DbaReportSaveDir   = "/home/mysql/dbareport/"
	RedisReportSaveDir = "/home/mysql/dbareport/redis/"
	ExporterConfDir    = "/home/mysql/.exporter"
	RedisReportLeftDay = 15
)

// tool path
const (
	DbToolsPath = "/home/mysql/dbtools"

	ZstdBin = "/home/mysql/dbtools/zstd"
)

// bk-dbmon path
const (
	BkDbmonPath        = "/home/mysql/bk-dbmon"
	BkDbmonBin         = "/home/mysql/bk-dbmon/bk-dbmon"
	BkDbmonConfFile    = "/home/mysql/bk-dbmon/dbmon-config.yaml"
	BkDbmonPort        = 6677
	BkDbmonHTTPAddress = "127.0.0.1:6677"
)

// backup
const (
	NormalBackupType  = "normal_backup"
	ForeverBackupType = "forever_backup"
	BackupClient      = "/usr/local/bin/backup_client"
)
