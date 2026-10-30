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

import "dbm-services/common/dbha-v2/internal/admin/cmds"

var (
	ConfigFilePath             = ""
	MigrateType                = ""
	MigrateInventory           = false
	MigrateInventoryFull       = false
	MigrateRepairMissing       = false
	MigrateRepairMissingSchema = false
	MigrateRepairMissingData   = false
)

func init() {
	MigrateCmd.Flags().StringVarP(&MigrateType, "type", "t", "all",
		"Migrate type: schema (structure only), data (data initialization only), all (schema then data)")

	MigrateCmd.Flags().BoolVar(&MigrateInventory, "inventory", false,
		"Read-only inventory of each endpoint; no schema, data, or ledger writes")
	MigrateCmd.Flags().BoolVar(&MigrateInventoryFull, "inventory-full", false,
		"Read-only inventory that also prints every column of each existing managed table")

	MigrateCmd.Flags().BoolVar(&MigrateRepairMissing, "repair-missing", false,
		"Repair missing schema objects and missing default data; only the parts run by --type are repaired")
	MigrateCmd.Flags().BoolVar(&MigrateRepairMissingSchema, "repair-missing-schema", false,
		"Rebuild missing tables, columns, and secondary indexes; rebuilt tables are empty and deleted rows are not restored")
	MigrateCmd.Flags().BoolVar(&MigrateRepairMissingData, "repair-missing-data", false,
		"Let data steps insert missing default rows when managed data already exists")

	StopCmd.Flags().BoolVarP(&cmds.ForceStop, "force", "f", false, "Force stop the process")
	StopCmd.Flags().IntVarP(&cmds.StopTimeout, "timeout", "t", 30, "Timeout in seconds for graceful stop")

	RestartCmd.Flags().BoolVarP(&cmds.ForceStop, "force", "f", false, "Force stop the process")
	RestartCmd.Flags().IntVarP(&cmds.StopTimeout, "timeout", "t", 30, "Timeout in seconds for graceful stop")

	ReloadCmd.Flags().BoolVarP(&cmds.ForceStop, "force", "f", false, "Force stop the process")
	ReloadCmd.Flags().IntVarP(&cmds.StopTimeout, "timeout", "t", 30, "Timeout in seconds for graceful stop")

	HealthCmd.Flags().BoolVarP(&cmds.JsonFormatter, "json", "j", false, "Output in JSON format")
}
