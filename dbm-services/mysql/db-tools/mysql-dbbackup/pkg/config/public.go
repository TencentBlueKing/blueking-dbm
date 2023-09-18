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

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

type Public struct {
	BkBizId          int    `ini:"BkBizId" validate:"required"`
	BkCloudId        int    `ini:"BkCloudId"`
	BillId           string `ini:"BillId"`
	BackupId         string `ini:"BackupId"`
	ClusterId        int    `ini:"ClusterId"`
	ClusterAddress   string `ini:"ClusterAddress"`
	ShardValue       int    `ini:"ShardValue"` // 分片 id，仅 spider 有用
	MysqlHost        string `ini:"MysqlHost" validate:"required,ip"`
	MysqlPort        int    `ini:"MysqlPort" validate:"required"`
	MysqlUser        string `ini:"MysqlUser" validate:"required"`
	MysqlPasswd      string `ini:"MysqlPasswd"`
	DataSchemaGrant  string `ini:"DataSchemaGrant" validate:"required"` // data,grant,priv,all
	BackupDir        string `ini:"BackupDir" validate:"required"`
	MysqlRole        string `ini:"MysqlRole" validate:"required"` // oneof=master slave
	MysqlCharset     string `ini:"MysqlCharset"`
	BackupTimeOut    string `ini:"BackupTimeout"`                                // 备份时间阈值，格式 09:00:01
	BackupType       string `ini:"BackupType" validate:"required"`               // oneof=logical physical
	OldFileLeftDay   int    `ini:"OldFileLeftDay"`                               // will remove old backup files before the days
	TarSizeThreshold uint64 `ini:"TarSizeThreshold" validate:"required,gte=128"` // tar file size. MB
	IOLimitMBPerSec  int    `ini:"IOLimitMBPerSec"`                              // tar speed, mb/s. 0 means no limit
	ResultReportPath string `ini:"ResultReportPath" validate:"required"`
	StatusReportPath string `ini:"StatusReportPath" validate:"required"`

	cnfFilename string
	targetName  string
}

// ParseDataSchemaGrant Check whether data|schema|grant is backed up
//func (c *Public) ParseDataSchemaGrant() error {
//	valueAllowed := []string{cst.BackupGrant, cst.BackupSchema, cst.BackupData, cst.BackupAll}
//	arr := strings.Split(c.DataSchemaGrant, ",")
//	set := make(map[string]struct{}, len(arr))
//	for _, v := range arr {
//		v = strings.ToLower(strings.TrimSpace(v))
//		if !cmutil.StringsHas(valueAllowed, v) {
//			return fmt.Errorf("the part of param DataSchemaGrant [%s] is wrong", v)
//		}
//		set[v] = struct{}{}
//	}
//	if _, found := set[cst.BackupData]; found {
//		common.BackupData = true
//	}
//	if _, found := set[cst.BackupSchema]; found {
//		common.BackupSchema = true
//	}
//	if _, found := set[cst.BackupGrant]; found {
//		common.BackupGrant = true
//	}
//	if _, found := set[cst.BackupAll]; found {
//		// all is alias to 'grant,schema,data'
//		common.BackupGrant = true
//		common.BackupData = true
//		common.BackupSchema = true
//	}
//
//	if !common.BackupData && !common.BackupSchema && !common.BackupGrant {
//		return fmt.Errorf("need to backup at least one of %v", valueAllowed)
//	}
//
//	return nil
//}

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
