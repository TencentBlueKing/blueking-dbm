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
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/logger"
)

func init() {
	// Objects Filter Options
	loadLogicalCmd.Flags().StringP("regex", "x", "", "Regular expression for 'db.table' matching")
	loadLogicalCmd.Flags().StringP("databases", "B", "", "Database to dump, default all")
	loadLogicalCmd.Flags().String("tables", "", "tables to dump, comma separated, default all")
	loadLogicalCmd.Flags().String("exclude-databases", "", "databases to dump, comma separated, default empty")
	loadLogicalCmd.Flags().String("exclude-tables", "", "tables to dump, comma separated, default empty")
	loadLogicalCmd.Flags().StringP("tables-list", "T", "", "Comma delimited table list to dump "+
		"(does not exclude regex option). Table name must include database name. For instance: test.t1,test.t2")
	viper.BindPFlag("LogicalLoad.Regex", loadLogicalCmd.Flags().Lookup("regex"))
	viper.BindPFlag("LogicalLoad.Databases", loadLogicalCmd.Flags().Lookup("databases"))
	viper.BindPFlag("LogicalLoad.Tables", loadLogicalCmd.Flags().Lookup("tables"))
	viper.BindPFlag("LogicalLoad.ExcludeDatabases", loadLogicalCmd.Flags().Lookup("exclude-databases"))
	viper.BindPFlag("LogicalLoad.ExcludeTables", loadLogicalCmd.Flags().Lookup("exclude-tables"))
	viper.BindPFlag("LogicalLoad.TablesList", loadLogicalCmd.Flags().Lookup("tables-list"))

	// Connection Options
	loadLogicalCmd.Flags().StringP("host", "h", "localhost", "The host to connect to, overwrite LogicalLoad.MysqlHost")
	loadLogicalCmd.Flags().IntP("port", "P", 3306, "TCP/IP port to connect to, overwrite LogicalLoad.MysqlPort")
	loadLogicalCmd.Flags().StringP("user", "u", "", "Username with the necessary privileges, "+
		"overwrite LogicalLoad.MysqlUser")
	loadLogicalCmd.Flags().StringP("password", "p", "", "User password, overwrite LogicalLoad.MysqlPasswd")
	loadLogicalCmd.Flags().String("charset", "", "User password, overwrite LogicalLoad.MysqlCharset")
	viper.BindPFlag("LogicalLoad.MysqlHost", loadLogicalCmd.Flags().Lookup("host"))
	viper.BindPFlag("LogicalLoad.MysqlPort", loadLogicalCmd.Flags().Lookup("port"))
	viper.BindPFlag("LogicalLoad.MysqlUser", loadLogicalCmd.Flags().Lookup("user"))
	viper.BindPFlag("LogicalLoad.MysqlPasswd", loadLogicalCmd.Flags().Lookup("password"))
	viper.BindPFlag("LogicalLoad.MysqlCharset", loadLogicalCmd.Flags().Lookup("charset"))

	// Control options
	loadLogicalCmd.Flags().Bool("enable-binlog", true, "overwrite LogicalLoad.EnableBinlog, "+
		"write binlog by default")
	loadLogicalCmd.Flags().String("databases-drop", "", "database list to drop, "+
		"overwrite LogicalLoad.DBListDropIfExists")
	viper.BindPFlag("LogicalLoad.EnableBinlog", loadLogicalCmd.Flags().Lookup("enable-binlog"))
	viper.BindPFlag("LogicalLoad.DBListDropIfExists", loadLogicalCmd.Flags().Lookup("databases-drop"))
}

var loadLogicalCmd = &cobra.Command{
	Use:          "logical",
	Short:        "logical load data dumped using mydumper or mysqldump",
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		defer func() {
			cmutil.ExecCommand(false, "", "chown", "-R", "mysql.mysql", cst.DbbackupGoInstallPath)
		}()
		cnf, err := initLoadCmd(cmd)
		if err != nil {
			return err
		}
		err = loadData(cnf, cst.BackupLogical)
		if err != nil {
			logger.Log.Error("Load Dbbackup: Failure. ", err.Error())
			return errors.WithMessage(err, "load data logical")
		}
		return nil
	},
}
