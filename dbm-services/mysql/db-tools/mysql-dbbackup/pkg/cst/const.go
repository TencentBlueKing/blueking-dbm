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
