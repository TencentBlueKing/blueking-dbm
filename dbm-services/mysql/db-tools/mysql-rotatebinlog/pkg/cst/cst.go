// Package cst TODO
package cst

import "time"

// DBTimeLayout TODO
const DBTimeLayout = time.RFC3339

// ReBinlogFilename binlog 文件名
const ReBinlogFilename = `binlog\d*\.\d+$`

const (
	// ReserveMinSizeMB 最少保留 binlog 大小
	ReserveMinSizeMB = 5 * 1
	// ReserveMinBinlogNum 最少保留的 binlog 个数, 以防 slave 拉取太慢
	ReserveMinBinlogNum = 10
	// ReduceStepSizeMB 删除的最小单位
	ReduceStepSizeMB = 5 * 1
	// MinKeepDuration 最少保留时间
	MinKeepDuration = 10 * time.Minute
)

const (
	RoleMaster       = "master"
	RoleSlave        = "slave"
	RoleRepeater     = "repeater"
	RoleSpiderMaster = "spider_master"
)

const (
	// BackupEnableTrue 启用备份上报，字符类型，不用 true，以免误解
	BackupEnableTrue = "yes"
	// BackupEnableFalse 不启用备份上报
	BackupEnableFalse = "no"
	// BackupEnableAuto 自动根据决定决定是否上报备份。目前仅 master 角色上报
	BackupEnableAuto = "auto"
)

var BackupEnableAllowed = []string{BackupEnableTrue, BackupEnableFalse, BackupEnableAuto, ""}

const OldRotateDir = "/home/mysql/rotate_logbin"
