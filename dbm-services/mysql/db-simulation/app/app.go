// Package app TODO
package app

const (
	// MySQL TODO
	MySQL = "mysql"
	// Spider TODO
	Spider = "spider"
	// Common 未选定集群时，只跑 MySQL 与 Spider 共有的语法检查
	Common = "common"
	// TdbCtl TODO
	TdbCtl = "tdbctl"

	// TendbCluster TODO
	TendbCluster = "tendbcluster"

	// SqlServer SQLServer 数据库类型标识
	SqlServer = "sqlserver"
)

const (
	TokudbEngine  = "tokudb"
	RocksdbEngine = "rocksdb"
	InnodbEngine  = "innodb"
)
