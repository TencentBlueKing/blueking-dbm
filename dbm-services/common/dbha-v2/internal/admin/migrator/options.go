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

package migrator

import "dbm-services/common/dbha-v2/pkg/storage/hamodel"

// managedDatabase is the schema owner. Tests may point it at a loopback database.
var managedDatabase = hamodel.DatabaseName

const (
	// MigrateTypeSchema migrates table schema only.
	MigrateTypeSchema = "schema"
	// MigrateTypeData runs every data step, including default strategies.
	MigrateTypeData = "data"
	// MigrateTypeAll migrates schema and then data.
	MigrateTypeAll = "all"

	// CreateDbIfNotExistSql creates the storage database with utf8mb4 if missing.
	CreateDbIfNotExistSql = "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"

	lockPrefix     = "dbha_migrate_"
	lockWaitSecond = 30
)

func lockName() string {
	return lockPrefix + managedDatabase
}

// Options controls one migrate invocation.
type Options struct {
	Type                string
	Inventory           bool
	AcceptMissingTables bool
	RepairMissing       bool
	RepairMissingTables bool
	RepairMissingData   bool
}

// RunsSchema reports whether this invocation may change schema.
func (o Options) RunsSchema() bool {
	return o.Type == MigrateTypeSchema || o.Type == MigrateTypeAll
}

// RunsData reports whether this invocation runs data steps.
func (o Options) RunsData() bool {
	return o.Type == MigrateTypeData || o.Type == MigrateTypeAll
}

// ValidType reports whether Type is a supported migrate mode.
func (o Options) ValidType() bool {
	switch o.Type {
	case MigrateTypeSchema, MigrateTypeData, MigrateTypeAll:
		return true
	default:
		return false
	}
}
