// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package config

import (
	"fmt"
	"regexp"
	"time"

	"golang.org/x/exp/slices"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

// Public 公共配置
type Public struct {
	// BkBizId bk_biz_id
	BkBizId int `ini:"BkBizId"`
	// BkCloudId 云区域id
	BkCloudId int `ini:"BkCloudId"`
	// BillId 备份单据id，例行备份为空，单据发起的备份请设置单据id
	BillId string `ini:"BillId"`
	// BackupId backup uuid，代表一次备份
	BackupId string `ini:"BackupId"`
	// ClusterId cluster_id
	ClusterId int `ini:"ClusterId"`
	// ClusterAddress cluster_domain
	ClusterAddress string `ini:"ClusterAddress" validate:"required"`
	// ShardValue for spider
	ShardValue int `ini:"ShardValue"` // 分片 id，仅 spider 有用
	// MysqlHost backup host
	MysqlHost string `ini:"MysqlHost" validate:"required,ip"`
	// MysqlPort backup port
	MysqlPort int `ini:"MysqlPort" validate:"required"`
	// MysqlUser backup user to login
	MysqlUser string `ini:"MysqlUser" validate:"required"`
	// MysqlPasswd backup user's password
	MysqlPasswd string `ini:"MysqlPasswd"`
	// DataSchemaGrant data,grant,schema,priv,all，写了 data 则只备data，不备份 schema
	DataSchemaGrant string `ini:"DataSchemaGrant" validate:"required"`
	// BackupDir backup files to save
	BackupDir string `ini:"BackupDir" validate:"required,dir"`
	MysqlRole string `ini:"MysqlRole"` // oneof=master slave
	// MysqlCharset 备份字符集，一般给逻辑备份使用，默认使用 character_set_server
	MysqlCharset string `ini:"MysqlCharset"`
	// BackupTimeOut 备份时间阈值，格式 09:00:01
	BackupTimeOut string `ini:"BackupTimeout"`
	// BackupType backup type,  oneof=logical physical auto
	// BackupTypeAuto 自动选择备份方式
	// 磁盘空间数据量大于 BackupTypeAutoDataSizeGB ，物理备份
	// glibc 版本小于 2.14，物理备份
	BackupType string `ini:"BackupType" validate:"required"`
	// OldFileLeftDay will remove old backup files before the days
	OldFileLeftDay int `ini:"OldFileLeftDay"`
	// TarSizeThreshold tar file size. MB
	TarSizeThreshold uint64 `ini:"TarSizeThreshold" validate:"gte=128"`
	// IOLimitMBPerSec tar speed, mb/s. 0 means no limit
	IOLimitMBPerSec int `ini:"IOLimitMBPerSec"`
	// IOLimitMasterFactor master机器专用限速因子，master io限速 = IOLimitMBPerSec * IOLimitMasterFactor
	IOLimitMasterFactor float64 `ini:"IOLimitMasterFactor"`
	StatusReportPath    string  `ini:"StatusReportPath"`
	// ReportPath 上报到 dbm 日志采集系统，为空则不写 log
	ReportPath string `ini:"ReportPath"`
	// NoCheckDiskSpace 不做空间检查. 但依然会先尝试本集群的全部旧全备
	NoCheckDiskSpace bool `ini:"NoCheckDiskSpace"`

	// EncryptOpt backup files encrypt options
	EncryptOpt *cmutil.EncryptOpt `ini:"EncryptOpt"`

	// KillLongQueryTime . if 0 not kill. Default 0
	// mydumper --kill-long-queries --long-query-guard xx: 发出 FTWRL 之前如果发现有超过这个时间的长 sql，则 kill 掉
	// xtrabackup --kill-long-queries-timeout: 发出 FTWRL 之后如果被阻塞，则等待多久之后把引起阻塞的长 sql kill 掉
	KillLongQueryTime int `ini:"KillLongQueryTime"`
	// FtwrlWaitTimeout 在发出 FTWRL 之前，如果有长 sql，则等待长 sql 多久后，放弃 ftwrl，放弃备份. Default 120s
	// 长 sql 的判断标准是 running time > --ftwrl-wait-threshold ( --lock-wait-threshold for 5.6)
	// xtrabackup --ftwrl-wait-timeout (--lock-wait-timeout for 5.6)
	// mydumper --long-query-guard
	FtwrlWaitTimeout int `ini:"FtwrlWaitTimeout"`
	// AcquireLockWaitTimeout If LOCK TABLES FOR BACKUP does not return within given timeout, abort the backup.
	// issue lock to mysqld: default 10s
	//  lock-ddl-timeout(xtrabackup57), backup-lock-timeout(xtrabackup80) --lock-wait-timeout(mydumper)
	AcquireLockWaitTimeout int `ini:"AcquireLockWaitTimeout"`
	// IsFullBackup 1: true, -1: false, 0: auto
	// 这个选项默认 0 代表会自动根据备份方式+备份对象 来决定是否将备份上报为全备
	// 某些情况只需要表结构，可以设置此选项强制上报为全备
	IsFullBackup int `ini:"IsFullBackup"`

	cnfFilename string
	targetName  string
}

// GetCnfFileName TODO
func (c *Public) GetCnfFileName() string {
	return c.cnfFilename
}

// SetCnfFileName TODO
func (c *Public) SetCnfFileName(filename string) {
	c.cnfFilename = filename
}

func (c *Public) splitDataSchemaGrant() []string {
	pattern := regexp.MustCompile(`\s*,\s*`)
	return pattern.Split(c.DataSchemaGrant, -1)
}

func (c *Public) IfBackupData() bool {
	return slices.Index(c.splitDataSchemaGrant(), cst.BackupAll) >= 0 ||
		slices.Index(c.splitDataSchemaGrant(), cst.BackupData) >= 0
}

func (c *Public) IfBackupSchema() bool {
	return slices.Index(c.splitDataSchemaGrant(), cst.BackupAll) >= 0 ||
		slices.Index(c.splitDataSchemaGrant(), cst.BackupSchema) >= 0
}

func (c *Public) IfBackupGrant() bool {
	return slices.Index(c.splitDataSchemaGrant(), cst.BackupAll) >= 0 ||
		slices.Index(c.splitDataSchemaGrant(), cst.BackupGrant) >= 0
}

// IfBackupGrantOnly 是否只备份权限
func (c *Public) IfBackupGrantOnly() bool {
	if c.IfBackupGrant() && !c.IfBackupData() && !c.IfBackupSchema() {
		return true
	}
	return false
}

func (c *Public) IfBackupAll() bool {
	if slices.Index(c.splitDataSchemaGrant(), cst.BackupAll) >= 0 {
		return true
	}
	isAll := true
	for _, i := range []string{cst.BackupData, cst.BackupSchema, cst.BackupGrant} {
		if slices.Index(c.splitDataSchemaGrant(), i) < 0 {
			isAll = false
		}
	}
	return isAll
}

// TargetName return targetName, will generate one when empty
func (c *Public) TargetName() string {
	if c.targetName == "" {
		currentTime := time.Now().Format("20060102150405")
		c.targetName = fmt.Sprintf("%d_%d_%s_%d_%s_%s",
			c.BkBizId, c.ClusterId, c.MysqlHost, c.MysqlPort, currentTime, c.BackupType) // rocksdb/tokudb

		logger.Log.Info("generate target name: ", c.targetName)
	}
	return c.targetName
}

func (c *Public) SetTargetName(targetName string) {
	c.targetName = targetName
}
