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
	// MaxKeepDurationMin 最少保留时间
	MaxKeepDurationMin = 10 * time.Minute
)

const (
	RoleMaster       = "master"
	RoleSlave        = "slave"
	RoleRepeater     = "repeater"
	RoleSpiderMaster = "spider_master"
)

const OldRotateDir = "/home/mysql/rotate_logbin"
