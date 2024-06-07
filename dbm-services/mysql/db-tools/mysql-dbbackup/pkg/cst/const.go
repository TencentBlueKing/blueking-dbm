// Package cst TODO
package cst

import "time"

const (
	// BackupGrant TODO
	BackupGrant = "grant"
	// BackupSchema TODO
	BackupSchema = "schema"
	// BackupData TODO
	BackupData = "data"
	// BackupAll 相当于 data,schema,grant
	BackupAll = "all"
	// BackupNone 不备份任何内容
	BackupNone = "none"
)

const (
	// RoleMaster lower case
	RoleMaster = "master"
	// RoleSlave TODO
	RoleSlave = "slave"
	// RoleRepeater TODO
	RoleRepeater = "repeater"
)

const (
	BackupPhysical = "physical"
	BackupLogical  = "logical"
)

const (
	// WrapperRemote TODO
	WrapperRemote = "mysql"
	// WrapperRemoteSlave TODO
	WrapperRemoteSlave = "mysql_slave"
	// WrapperSpider TODO
	WrapperSpider = "SPIDER"
	// WrapperTdbctl TODO
	WrapperTdbctl = "TDBCTL"
	// ServerNamePrefix TODO
	ServerNamePrefix = "SPT"
)

// INFODBA_SCHEMA TODO
const INFODBA_SCHEMA = "infodba_schema"

const (
	// SpiderScheduleWaitTimeout TODO
	SpiderScheduleWaitTimeout = 48 * time.Hour
	// SpiderRemoveOldTaskBeforeDays 不少于 14 day
	SpiderRemoveOldTaskBeforeDays = 30
	// SpiderTaskMaxRunHours TODO
	SpiderTaskMaxRunHours = 48
)

// SpiderNodeShardValue spider 全局备份，对 spider 节点备份假设的 shard_value 值
// 比如 为 0，则 spider node 备份任务会写到 spt0 节点，spider node备份任务查询spider表时，实际是从 spt0 获取的
// 注意不能指定负数，因为 -1 mod 2 的结果也为负数，会无法写入数据
const SpiderNodeShardValue = 0

// ZstdSuffix zstd compress file suffix
const ZstdSuffix = ".zst"

const (
	MydumperTimeLayout   = "2006-01-02 15:04:05"
	XtrabackupTimeLayout = "2006-01-02 15:04:05"
)

const (
	// FileSchema TODO
	FileSchema = "schema"
	// FileData TODO
	FileData = "data"
	// FileMetadata TODO
	FileMetadata = "metadata"
	// FileOther TODO
	FileOther = "other"
	// FilePriv TODO
	FilePriv = "priv"
	// FilePart tar part
	FilePart  = "part"
	FileTar   = "tar"
	FileIndex = "index"
)

const DBAReportBase = "/home/mysql/dbareport"

const MysqlCrondUrl = "http://127.0.0.1:9999"

const MysqlRotateBinlogInstallPath = "/home/mysql/mysql-rotatebinlog"
