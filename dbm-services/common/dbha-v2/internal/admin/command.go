/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package admin

import (
	"dbm-services/common/dbha-v2/internal/admin/cmds"
	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/internal/admin/migrator"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/version"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var VersionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print Version Information",
	Run: func(cmd *cobra.Command, args []string) {
		version.Print("DBHA Admin Server")
	},
}

var MigrateCmd = &cobra.Command{
	Use:   "migrate",
	Short: "migrate database schema and data steps",
	Long: `Migrate command supports the following types:
  --type schema : only migrate table schema
  --type data   : run data initialization steps
  --type all    : migrate schema and then initialize data (default)

		--inventory reports endpoint class without writing.
		--inventory-full prints every column of each existing managed table. It is read-only and does not require --inventory.
		--repair-missing-schema rebuilds missing tables, columns, and secondary indexes. It also
		confirms empty-table creation when only some tables exist. Rebuilt tables are empty;
		a rebuilt strategy table stays empty unless data repair is also set.
		--repair-missing-data lets data steps insert missing default rows when managed data exists.
		--repair-missing sets both repairs; only the parts run by --type are repaired.
		The current data step initializes default strategies. Soft-deleted strategy rows stay
		deleted. An empty strategy table receives its default rows only when data version 1
		is absent. When that ledger row already exists, the empty table stays empty unless
		--repair-missing-data is set.
		Schema and all modes may lock managed tables while converging primary keys and column
		definitions. Stop writes to those tables first. This command cannot detect that.`,
	RunE: runMigrate,
}

// HealthCmd is used to show the health information of this process.
var HealthCmd = &cobra.Command{
	Use:   "health",
	Short: "Show the health information of this process",
	RunE:  cmds.HealthCmdRunE,
}

// StartCmd is used to start this process in background (daemon mode).
var StartCmd = &cobra.Command{
	Use:   "start",
	Short: "Start this process.",
	RunE:  cmds.StartCmdRunE,
}

// DaemonStartCmd is used to start this process with a guard that restarts it on abnormal exit.
var DaemonStartCmd = &cobra.Command{
	Use:   "daemon-start",
	Short: "Start this process with guard (auto-restart on crash).",
	RunE:  cmds.DaemonStartCmdRunE,
}

// StopCmd is used to stop this process.
var StopCmd = &cobra.Command{
	Use:   "stop",
	Short: "Stop this process.",
	RunE:  cmds.StopCmdRunE,
}

// RestartCmd is used to restart this process.
var RestartCmd = &cobra.Command{
	Use:   "restart",
	Short: "Restart this process.",
	RunE:  cmds.RestartCmdRunE,
}

// ReloadCmd is used to reload this process.
var ReloadCmd = &cobra.Command{
	Use:   "reload",
	Short: "Reload this process.",
	RunE:  cmds.ReloadCmdRunE,
}

func runMigrate(cmd *cobra.Command, args []string) error {
	// Determine the config source: ./etc/admin.yaml by default, explicit path takes precedence
	viper.SetConfigName("admin")
	viper.SetConfigType("yaml")
	viper.AddConfigPath("./etc")
	logger.Info("use the configuration, path: %s", ConfigFilePath)
	if ConfigFilePath != "" {
		viper.SetConfigFile(ConfigFilePath)
	}

	// Read the configuration
	if err := viper.ReadInConfig(); err != nil {
		logger.Error("read admin configuration failed, errmsg: %s", err)
		return err
	}

	// Unmarshal the configuration into the global config
	if err := viper.Unmarshal(&config.Cfg); err != nil {
		logger.Error("unmarshal admin configuration failed, errmsg: %s", err)
		return err
	}

	// Log the migrate type for non-inventory modes
	if !MigrateInventory && !MigrateInventoryFull {
		logger.Info("migrate type: %s", MigrateType)
	}

	// Run the migration
	err := migrator.Run(migrator.Options{
		Type:                MigrateType,
		Inventory:           MigrateInventory,
		RepairMissing:       MigrateRepairMissing,
		RepairMissingSchema: MigrateRepairMissingSchema,
		RepairMissingData:   MigrateRepairMissingData,
		InventoryFull:       MigrateInventoryFull,
		Report:              cmd.OutOrStdout(),
	})

	// Log and return the migration error
	if err != nil {
		logger.Error("migrate failed, errmsg: %s", err)
	}
	return err
}
