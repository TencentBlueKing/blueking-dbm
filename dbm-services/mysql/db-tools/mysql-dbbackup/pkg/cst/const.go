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
	// BackupAll TODO
	BackupAll = "all"
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
	// SpiderRemoveOldTaskBeforeDays TODO
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
