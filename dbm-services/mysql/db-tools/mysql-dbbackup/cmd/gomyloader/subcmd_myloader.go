// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package main

import (
	"github.com/spf13/cobra"
)

func init() {
	// Objects Filter Options
	myloaderCmd.Flags().StringP("regex", "x", "", "Regular expression for 'db.table' matching")
	myloaderCmd.Flags().StringP("databases", "B", "", "Database to dump, default all")
	myloaderCmd.Flags().String("tables", "", "tables to dump, comma separated, default all")
	myloaderCmd.Flags().String("exclude-databases", "", "databases to dump, comma separated, default empty")
	myloaderCmd.Flags().String("exclude-tables", "", "tables to dump, comma separated, default empty")
	myloaderCmd.Flags().StringP("tables-list", "T", "", "Comma delimited table list to dump "+
		"(does not exclude regex option). Table name must include database name. For instance: test.t1,test.t2")
	myloaderCmd.Flags().Bool("no-data", false, "Do not import table data")
	myloaderCmd.Flags().Bool("skip-post", false, "Do not import events, stored procedures and functions")
	myloaderCmd.Flags().Bool("skip-triggers", false, "Do not import triggers")
	myloaderCmd.Flags().BoolP("drop-table-if-exists", "o", false, "Drop tables if they already exist")
	myloaderCmd.Flags().String("rewrite-db", "", "database names to rewrite from xx to yy when importing")

	myloaderCmd.Flags().Int("max-threads-for-schema-creation", 4, "Maximum number of threads for schema creation")

	myloaderCmd.Flags().StringP("host", "h", "localhost", "The host to connect to, overwrite LogicalLoad.MysqlHost")
	myloaderCmd.Flags().IntP("port", "P", 3306, "TCP/IP port to connect to, overwrite LogicalLoad.MysqlPort")
	myloaderCmd.Flags().StringP("user", "u", "", "Username with the necessary privileges, "+
		"overwrite LogicalLoad.MysqlUser")
	myloaderCmd.Flags().StringP("password", "p", "", "User password, overwrite LogicalLoad.MysqlPasswd")
	myloaderCmd.Flags().String("charset", "", "User password, overwrite LogicalLoad.MysqlCharset")
	myloaderCmd.Flags().StringP("socket", "S", "", "The socket file to use for connection")

	myloaderCmd.Flags().IntP("verbose", "v", 1, "Write more. (-v 3 gives the table output format)")
	myloaderCmd.Flags().BoolP("force", "f", false, "Continue even if we get an SQL error")
	myloaderCmd.Flags().StringP("logfile", "L", "", "Use a specific defaults file. Default: /etc/myloader.cnf")
	myloaderCmd.Flags().StringP("directory", "d", "", "Directory of the dump to import")
	//myloaderCmd.Flags().String("defaults-file", "", "Use a specific defaults file. Default: /etc/myloader.cnf")
	myloaderCmd.Flags().String("init-command", "", "SQL Command to execute when connecting to MySQL server")

	// --resume
	//--skip-definer
	// Control options
	myloaderCmd.Flags().BoolP("enable-binlog", "e", false, "overwrite LogicalLoad.EnableBinlog")
	myloaderCmd.Flags().String("databases-drop", "", "database list to drop, "+
		"overwrite LogicalLoad.DBListDropIfExists")
	myloaderCmd.PersistentFlags().IntP("threads", "t", 4, "Number of threads to use, default 4")
}

var myloaderCmd = &cobra.Command{
	Use:          "myloader",
	Short:        "myloader",
	SilenceUsage: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		return nil
	},
}

// myloader 将旧的 .info 格式转换成新的 .index 格式
// 让旧备份兼容回档逻辑
func myloader(cmd *cobra.Command, args []string) (errs error) {
	return nil
}
