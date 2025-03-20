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
	UnixtimeLayout = "2006-01-02 15:04:05"
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

// backup
const (
	BackupClientStrorageTypeCOS  = "cos"
	BackupClientStrorageTypeHDFS = "hdfs"
)

// IsMongo TODO
func IsMongo(clusterType string) bool {
	if clusterType == MongoTypeShardedCluster || clusterType == MongoTypeReplicaSet || clusterType == MongoTypeStandalone {
		return true
	}
	return false
}
