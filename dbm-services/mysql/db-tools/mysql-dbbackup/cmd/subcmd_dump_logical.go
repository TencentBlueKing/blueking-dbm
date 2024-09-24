/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cmd

import (
	"github.com/pkg/errors"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

func init() {
	dumpLogicalCmd.Flags().StringP("config", "c", "",
		"config file to backup, other options will overwrite this config file temporary")

	// Objects Filter Options
	dumpLogicalCmd.Flags().StringP("regex", "x", "", "Regular expression for 'db.table' matching")
	dumpLogicalCmd.Flags().StringP("databases", "B", "", "Database to dump, default all")
	dumpLogicalCmd.Flags().String("tables", "", "tables to dump, comma separated, default all")
	dumpLogicalCmd.Flags().String("exclude-databases", "", "databases to dump, comma separated, default empty")
	dumpLogicalCmd.Flags().String("exclude-tables", "", "tables to dump, comma separated, default empty")
	dumpLogicalCmd.Flags().StringP("tables-list", "T", "", "Comma delimited table list to dump "+
		"(does not exclude regex option). Table name must include database name. For instance: test.t1,test.t2")
	viper.BindPFlag("LogicalBackup.Regex", dumpLogicalCmd.Flags().Lookup("regex"))
	viper.BindPFlag("LogicalBackup.Databases", dumpLogicalCmd.Flags().Lookup("databases"))
	viper.BindPFlag("LogicalBackup.Tables", dumpLogicalCmd.Flags().Lookup("tables"))
	viper.BindPFlag("LogicalBackup.ExcludeDatabases", dumpLogicalCmd.Flags().Lookup("exclude-databases"))
	viper.BindPFlag("LogicalBackup.ExcludeTables", dumpLogicalCmd.Flags().Lookup("exclude-tables"))
	viper.BindPFlag("LogicalBackup.TablesList", dumpLogicalCmd.Flags().Lookup("tables-list"))
	//dumpLogicalCmd.Flags().String("where", "", "Dump only selected records")

	// logical common options bind
	dumpLogicalCmd.Flags().BoolP("no-data", "d", false, "tables to dump, comma separated")
	dumpLogicalCmd.Flags().BoolP("no-schemas", "m", false, "Do not dump table data")
	//dumpLogicalCmd.Flags().BoolP("no-views", "W", false, "Do not dump VIEWs")
	dumpLogicalCmd.Flags().BoolP("triggers", "G", false, "Dump triggers. By default, it do not dump triggers")
	dumpLogicalCmd.Flags().BoolP("events", "E", false, "Dump stored procedures and functions. "+
		"By default, it do not dump stored procedures nor functions")
	dumpLogicalCmd.Flags().BoolP("routines", "R", false, "Dump events. By default, it do not dump events")
	viper.BindPFlag("LogicalBackup.NoData", dumpLogicalCmd.Flags().Lookup("no-data"))
	viper.BindPFlag("LogicalBackup.NoSchemas", dumpLogicalCmd.Flags().Lookup("no-schemas"))
	//viper.BindPFlag("LogicalBackup.NoViews", dumpLogicalCmd.Flags().Lookup("no-views"))
	viper.BindPFlag("LogicalBackup.Triggers", dumpLogicalCmd.Flags().Lookup("triggers"))
	viper.BindPFlag("LogicalBackup.Events", dumpLogicalCmd.Flags().Lookup("events"))
	viper.BindPFlag("LogicalBackup.Routines", dumpLogicalCmd.Flags().Lookup("routines"))

	dumpLogicalCmd.Flags().String("use-mysqldump", "no", "no, yes, auto, overwrite LogicalBackup.UseMysqldump")
	dumpLogicalCmd.Flags().Int("threads", 4, "threads for mydumper")

	viper.BindPFlag("LogicalBackup.UseMysqldump", dumpLogicalCmd.Flags().Lookup("use-mysqldump"))
	viper.BindPFlag("LogicalBackup.Threads", dumpLogicalCmd.Flags().Lookup("threads"))
}

var dumpLogicalCmd = &cobra.Command{
	Use:          "logical",
	Short:        "logical dump using mydumper or mysqldump",
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		var err error
		if err = logger.InitLog("dbbackup_dump.log"); err != nil {
			return err
		}
		var cnf = config.BackupConfig{}
		config.SetDefaults()
		// --config 不提供时，全部由命令行提供选项
		if configFile, err := cmd.Flags().GetString("config"); err != nil {
			return err
		} else if configFile != "" {
			if err = cmutil.FileExistsErr(configFile); err != nil {
				return err
			}
			if err = initConfig(configFile, &cnf); err != nil {
				logger.Log.Error("Create Dbbackup: fail to parse ", configFile)
				return errors.WithMessagef(err, "fail to parse %s", configFile)
			}
			if cnf.LogicalBackup.GetFilterType() == config.FilterTypeForm {
				logger.Log.Info("set Regex/TablesList to empty for form filter type ", configFile)
				cnf.LogicalBackup.Regex = ""
				cnf.LogicalBackup.TablesList = ""
			}
		}
		if err = viper.Unmarshal(&cnf); err != nil {
			return err
		}
		cnf.Public.BackupType = cst.BackupLogical
		if cnf.Public.EncryptOpt != nil {
			cnf.Public.EncryptOpt.EncryptEnable = false
		}

		cnf.PhysicalBackup = config.PhysicalBackup{}
		cnf.PhysicalLoad = config.PhysicalLoad{}
		cnf.Public.SetFlagFullBackup(-1) // dumplogical command 一律不认为是 full backup，不可用于全库恢复
		err = backupData(&cnf)
		if err != nil {
			logger.Log.Error("dumpbackup logical failed", err.Error())
		}
		return err
	},
}
