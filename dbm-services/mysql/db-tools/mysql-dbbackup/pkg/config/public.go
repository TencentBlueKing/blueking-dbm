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
	BkBizId int `ini:"BkBizId" validate:"required"`
	// BkCloudId 云区域id
	BkCloudId int `ini:"BkCloudId"`
	// BillId 备份单据id，例行备份为空，单据发起的备份请设置单据id
	BillId string `ini:"BillId"`
	// BackupId backup uuid，代表一次备份
	BackupId string `ini:"BackupId"`
	// ClusterId cluster_id
	ClusterId int `ini:"ClusterId"`
	// ClusterAddress cluster_domain
	ClusterAddress string `ini:"ClusterAddress"`
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
	BackupDir    string `ini:"BackupDir" validate:"required"`
	MysqlRole    string `ini:"MysqlRole" validate:"required"` // oneof=master slave
	MysqlCharset string `ini:"MysqlCharset"`
	// BackupTimeOut 备份时间阈值，格式 09:00:01
	BackupTimeOut string `ini:"BackupTimeout"`
	// BackupType backup type,  oneof=logical physical
	BackupType string `ini:"BackupType" validate:"required"`
	// OldFileLeftDay will remove old backup files before the days
	OldFileLeftDay int `ini:"OldFileLeftDay"`
	// TarSizeThreshold tar file size. MB
	TarSizeThreshold uint64 `ini:"TarSizeThreshold" validate:"required,gte=128"`
	// IOLimitMBPerSec tar speed, mb/s. 0 means no limit
	IOLimitMBPerSec  int    `ini:"IOLimitMBPerSec"`
	ResultReportPath string `ini:"ResultReportPath" validate:"required"`
	StatusReportPath string `ini:"StatusReportPath" validate:"required"`

	// EncryptOpt backup files encrypt options
	EncryptOpt *cmutil.EncryptOpt `ini:"EncryptOpt"`

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

func (c *Public) TargetName() string {
	if c.targetName == "" {
		currentTime := time.Now().Format("20060102_150405")
		c.targetName = fmt.Sprintf("%d_%d_%s_%d_%s_%s",
			c.BkBizId, c.ClusterId, c.MysqlHost, c.MysqlPort, currentTime, c.BackupType)

		logger.Log.Info("generate target name: ", c.targetName)
	}
	return c.targetName
}
