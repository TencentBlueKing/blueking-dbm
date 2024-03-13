// Package consts 常量
package consts

// BkDbmonVersion version
const (
	BkDbmonVersion = "v0.14"
)

const (

	// MongoTypeShardedCluster TODO
	MongoTypeShardedCluster = "MongoShardedCluster"
	// MongoTypeReplicaSet TODO
	MongoTypeReplicaSet = "MongoReplicaSet"
	// MongoTypeStandalone TODO
	MongoTypeStandalone = "MongoStandalone"
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
	UsrLocal         = "/usr/local"
	PackageSavePath  = "/data/install"
	Data1Path        = "/data1"
	DataPath         = "/data"
	DbaReportSaveDir = "/home/mysql/dbareport/"
)

// tool path
const (
	DbToolsPath = "/home/mysql/dbtools/"
	RedisCliBin = "/home/mysql/dbtools/redis-cli"
)

// backup
const (
	IBSBackupClient = "/usr/local/bin/backup_client"
	COSBackupClient = "/usr/local/backup_client/bin/backup_client"
	COSInfoFile     = "/home/mysql/.cosinfo.toml"

	RedisFullBackupReportType   = "redis_fullbackup"
	RedisBinlogBackupReportType = "redis_binlogbackup"

	MongoBackupRepoter = "mongo_backup_report_%s.log"

	BackupClientStrorageTypeCOS  = "cos"
	BackupClientStrorageTypeHDFS = "hdfs"
)

const (
	// PayloadFormatRaw raw
	PayloadFormatRaw = "raw"
	// PayloadFormatBase64 base64
	PayloadFormatBase64 = "base64"
)

// IsMongo TODO
func IsMongo(clusterType string) bool {
	if clusterType == MongoTypeShardedCluster || clusterType == MongoTypeReplicaSet || clusterType == MongoTypeStandalone {
		return true
	}
	return false
}
