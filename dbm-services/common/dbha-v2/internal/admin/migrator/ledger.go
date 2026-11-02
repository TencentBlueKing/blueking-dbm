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

import (
	"fmt"
	"sync"
	"time"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// ledgerKeyed is a ledger row that exposes its version and name.
type ledgerKeyed interface {
	ledgerKey() (int64, string)
}

var (
	schemaLedgerSpecOnce = sync.OnceValues(func() (tableSpec, error) { return reflectTable(schemaLedgerRow{}) })
	dataLedgerSpecOnce   = sync.OnceValues(func() (tableSpec, error) { return reflectTable(dataLedgerRow{}) })
)

// schemaLedgerRow is one row of the schema ledger. It is the single definition of the ledger
// columns; the frozen CREATE statement in schemaLedgerSQL must stay consistent with it.
type schemaLedgerRow struct {
	Version   int64     `gorm:"column:version;primaryKey"`
	Name      string    `gorm:"column:name;type:varchar(255);not null;uniqueIndex:uk_schema_migration_name"`
	AppliedAt time.Time `gorm:"column:applied_at;type:datetime;not null"`
}

// dataLedgerRow is one row of the data ledger. The frozen CREATE statement in dataLedgerSQL
// must stay consistent with it.
type dataLedgerRow struct {
	Version               int64     `gorm:"column:version;primaryKey"`
	Name                  string    `gorm:"column:name;type:varchar(255);not null;uniqueIndex:uk_data_migration_name"`
	RequiredSchemaVersion int64     `gorm:"column:required_schema_version;not null"`
	AppliedAt             time.Time `gorm:"column:applied_at;type:datetime;not null"`
}

// TableName returns the schema ledger table name.
func (schemaLedgerRow) TableName() string { return schemaLedgerTable }

func (row schemaLedgerRow) ledgerKey() (int64, string) { return row.Version, row.Name }

// TableName returns the data ledger table name.
func (dataLedgerRow) TableName() string { return dataLedgerTable }

func (row dataLedgerRow) ledgerKey() (int64, string) { return row.Version, row.Name }

// ledgerSpecs returns the reflected specs of both ledger tables, computed once per process.
// Ledger tables are not managed tables: they never get schema steps.
// The specs share slices with the cache, so callers must treat them as read-only.
func ledgerSpecs() (tableSpec, tableSpec, error) {
	schemaSpec, err := schemaLedgerSpecOnce()
	if err != nil {
		return tableSpec{}, tableSpec{}, err
	}
	dataSpec, err := dataLedgerSpecOnce()
	if err != nil {
		return tableSpec{}, tableSpec{}, err
	}

	return schemaSpec, dataSpec, nil
}

// recordLedger inserts one ledger row, refusing to rename a version that is already recorded.
// label prefixes the conflict error, for example "ledger" or "data ledger".
func recordLedger[T ledgerKeyed](db *gorm.DB, row T, label string) error {
	version, name := row.ledgerKey()

	var found []T
	err := db.Where(clause.Eq{Column: clause.PrimaryColumn, Value: version}).Limit(1).Find(&found).Error
	if err != nil {
		return err
	}
	if len(found) > 0 {
		if _, existing := found[0].ledgerKey(); existing != name {
			return fmt.Errorf("%s name conflict, version: %d", label, version)
		}
		return nil
	}

	return db.Create(&row).Error
}

// readLedgerRows reads every row of one ledger table into dest, keyed by version.
func readLedgerRows[T ledgerKeyed](db *gorm.DB, dest map[int64]Ledger) error {
	var rows []T
	if err := db.Find(&rows).Error; err != nil {
		return err
	}

	for _, row := range rows {
		version, name := row.ledgerKey()
		dest[version] = Ledger{Version: version, Name: name}
	}

	return nil
}

// serverNow reads the current time from the server clock.
func serverNow(db *gorm.DB) (time.Time, error) {
	var now time.Time
	err := db.Raw("SELECT NOW()").Row().Scan(&now)

	return now, err
}
