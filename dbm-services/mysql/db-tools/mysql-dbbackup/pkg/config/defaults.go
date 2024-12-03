/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package config

import (
	"github.com/spf13/viper"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
)

// SetDefaults vip set defaults
func SetDefaults() {
	viper.SetDefault("Public.OldFileLeftDay", 2)
	viper.SetDefault("Public.TarSizeThreshold", 8192)
	viper.SetDefault("Public.IOLimitMBPerSec", 300)
	viper.SetDefault("Public.IOLimitMasterFactor", 0.5)
	viper.SetDefault("Public.BackupDir", "/data/dbbak")
	//viper.SetDefault("Public.MysqlCharset", "binary")
	viper.SetDefault("Public.BackupTimeOut", "09:00:01")
	viper.SetDefault("Public.KillLongQueryTime", 0)
	viper.SetDefault("Public.FtwrlWaitTimeout", 120)
	viper.SetDefault("Public.AcquireLockWaitTimeout", 10)

	viper.SetDefault("PhysicalBackup.MaxMyisamTables", 10)
	viper.SetDefault("PhysicalBackup.DisableSlaveMultiThread", false)
	viper.SetDefault("LogicalBackup.Threads", 4)
	viper.SetDefault("LogicalBackup.InsertMode", "insert")
	viper.SetDefault("LogicalBackup.UseMysqldump", cst.LogicalMysqldumpAuto)
}
