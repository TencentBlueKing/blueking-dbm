//go:build integration

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
	"bytes"
	"context"
	"os"
	"strings"
	"testing"
	"time"
)

func TestMySQLMigrateGaps(t *testing.T) {
	previous := managedDatabase
	managedDatabase = "dbha_migrate_itest"
	t.Cleanup(func() { managedDatabase = previous })
	store := openLoopbackMySQL(t, mysqlPort())
	t.Cleanup(func() { dropManaged(t, store) })

	t.Run("missing-index", func(t *testing.T) { testMissingIndex(t, store) })
	t.Run("same-name-index-conflict", func(t *testing.T) { testSameNameIndexConflict(t, store) })
	t.Run("hard-deleted-strategies", func(t *testing.T) { testHardDeletedStrategies(t, store) })
	t.Run("complete-second-all", func(t *testing.T) { testCompleteSecondAll(t, store) })
	t.Run("inventory", func(t *testing.T) { testMySQLInventory(t, store) })
	t.Run("data-ledger-name-conflict", func(t *testing.T) { testDataLedgerNameConflict(t, store) })
	t.Run("data-ledger-shape", func(t *testing.T) { testDataLedgerShape(t, store) })
	t.Run("lock-reentry", func(t *testing.T) { testLockReentry(t) })
	t.Run("lock-wait-restored", func(t *testing.T) { testLockWaitRestored(t, store) })
}

func testMissingIndex(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	mustRun(t, Options{Type: MigrateTypeSchema}, store)
	step := findStep(objectIndex, "t_db_switching_log", "", "idx_level")
	drop := "ALTER TABLE `t_db_switching_log` DROP INDEX `idx_level`"

	mustExec(t, store, drop)
	mustExec(t, store, "DELETE FROM `schema_migrations` WHERE version = ?", step.Version)
	mustRun(t, Options{Type: MigrateTypeSchema}, store)
	if !indexExists(t, store, step.Table, step.Index) {
		t.Fatal("unrecorded missing index was not added")
	}

	mustExec(t, store, drop)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err == nil {
		t.Fatal("recorded index loss should be drift")
	}
	if indexExists(t, store, step.Table, step.Index) {
		t.Fatal("drift recreated the index")
	}

	mustRun(t, Options{Type: MigrateTypeSchema, RepairMissing: true}, store)
	if !indexExists(t, store, step.Table, step.Index) {
		t.Fatal("repair-missing did not rebuild the index")
	}
	applied := ledgerTime(t, store, "schema_migrations", step.Version)
	mustRun(t, Options{Type: MigrateTypeSchema}, store)
	if !indexExists(t, store, step.Table, step.Index) ||
		ledgerTime(t, store, "schema_migrations", step.Version) != applied {
		t.Fatal("second schema run changed the repaired index")
	}
}

func testSameNameIndexConflict(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	mustRun(t, Options{Type: MigrateTypeSchema}, store)
	step := findStep(objectIndex, strategyTableName(), "", "idx_description")
	mustExec(t, store, "ALTER TABLE `t_db_switching_strategy` DROP INDEX `idx_description`")
	mustExec(t, store, "ALTER TABLE `t_db_switching_strategy` ADD INDEX `idx_description` (`description`(10))")
	ledgers := schemaLedgerRows(t, store)

	err := run(Options{Type: MigrateTypeSchema, RepairMissingSchema: true}, []Store{store})
	if err == nil || !strings.Contains(err.Error(), "result: conflict") {
		t.Fatalf("same-name index should be a conflict, errmsg: %v", err)
	}
	found := false
	for _, idx := range mustLoad(t, store).Tables[step.Table].Indexes {
		if idx.Name != step.Index {
			continue
		}
		found = true
		if len(idx.Prefix) == 0 || idx.Prefix[0] != 10 {
			t.Fatalf("conflict changed the index, prefix: %v", idx.Prefix)
		}
	}
	if !found {
		t.Fatal("conflict dropped the index")
	}
	if schemaLedgerRows(t, store) != ledgers {
		t.Fatal("conflict wrote the schema ledger")
	}
}

func testHardDeletedStrategies(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	mustRun(t, Options{Type: MigrateTypeAll}, store)
	mustExec(t, store, "DELETE FROM `t_db_switching_strategy`")

	mustRun(t, Options{Type: MigrateTypeData}, store)
	if strategyCount(t, store) != 0 || dataLedgerRows(t, store) != 1 {
		t.Fatal("hard-deleted defaults were reseeded without repair")
	}
	mustRun(t, Options{Type: MigrateTypeData, RepairMissingData: true}, store)
	if strategyCount(t, store) != len(defaultStrategies()) || dataLedgerRows(t, store) != 1 {
		t.Fatal("repair-missing-data did not reseed the hard-deleted defaults")
	}
}

func testCompleteSecondAll(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	mustRun(t, Options{Type: MigrateTypeAll}, store)
	version := schemaSteps()[0].Version
	event := defaultStrategies()[0].TriggerEventName.String()
	applied := ledgerTime(t, store, "schema_migrations", version)
	ledgers := schemaLedgerRows(t, store)
	updated := strategyTime(t, store, event)

	mustRun(t, Options{Type: MigrateTypeAll}, store)
	if ledgerTime(t, store, "schema_migrations", version) != applied || schemaLedgerRows(t, store) != ledgers {
		t.Fatal("second all changed the schema ledger")
	}
	if strategyTime(t, store, event) != updated || strategyCount(t, store) != len(defaultStrategies()) {
		t.Fatal("second all changed strategy rows")
	}
	if dataLedgerRows(t, store) != 1 {
		t.Fatal("second all changed the data ledger")
	}
}

func testMySQLInventory(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	var output bytes.Buffer
	mustRun(t, Options{Inventory: true, Report: &output}, store)
	if !strings.Contains(output.String(), "class: empty") || !strings.Contains(output.String(), "result: ok") {
		t.Fatalf("empty inventory, report: %s", output.String())
	}
	if mustLoad(t, store).Database {
		t.Fatal("inventory created the database")
	}

	mustRun(t, Options{Type: MigrateTypeAll}, store)
	strategies, ledgers := strategyCount(t, store), schemaLedgerRows(t, store)
	output.Reset()
	mustRun(t, Options{Inventory: true, Report: &output}, store)
	if !strings.Contains(output.String(), "class: complete") || !strings.Contains(output.String(), "result: ok") {
		t.Fatalf("complete inventory, report: %s", output.String())
	}
	if strategyCount(t, store) != strategies || schemaLedgerRows(t, store) != ledgers {
		t.Fatal("inventory wrote rows")
	}
}

func testDataLedgerNameConflict(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	mustRun(t, Options{Type: MigrateTypeAll}, store)
	other := defaultStrategies()[1].TriggerEventName.String()
	mustExec(t, store, "UPDATE `"+dataLedgerTable+"` SET name = 'other_ledger' WHERE version = ?", dataVersion)
	mustExec(t, store, "DELETE FROM `t_db_switching_strategy` WHERE trigger_event_name = ?", other)

	err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store})
	if err == nil || !strings.Contains(err.Error(), "data ledger name conflict") {
		t.Fatalf("data ledger conflict was not reported, errmsg: %v", err)
	}
	if strategyCount(t, store) != len(defaultStrategies())-1 {
		t.Fatal("failed data transaction kept the inserted strategy")
	}
	if dataLedgerName(t, store) != "other_ledger" {
		t.Fatal("failed data transaction rewrote the data ledger")
	}
}

func testDataLedgerShape(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	mustRun(t, Options{Type: MigrateTypeAll}, store)
	other := defaultStrategies()[1].TriggerEventName.String()
	mustExec(t, store, "DROP TABLE `"+dataLedgerTable+"`")
	mustExec(t, store, "CREATE TABLE `"+dataLedgerTable+"` (`version` bigint NOT NULL, "+
		"`name` varchar(255) NOT NULL, PRIMARY KEY (`version`), UNIQUE KEY `uk_name` (`name`))")
	mustExec(t, store, "DELETE FROM `t_db_switching_strategy` WHERE trigger_event_name = ?", other)

	err := run(Options{Type: MigrateTypeAll, RepairMissingData: true}, []Store{store})
	if err == nil || !strings.Contains(err.Error(), "migration ledger conflict") {
		t.Fatalf("malformed data ledger was not blocked, errmsg: %v", err)
	}
	if strategyCount(t, store) != len(defaultStrategies())-1 || dataLedgerRows(t, store) != 0 {
		t.Fatal("blocked migrate wrote strategies or the data ledger")
	}

	var output bytes.Buffer
	err = run(Options{Inventory: true, Report: &output}, []Store{store})
	if err == nil || !strings.Contains(err.Error(), "structural conflict") {
		t.Fatalf("inventory missed the malformed data ledger, errmsg: %v", err)
	}
	if !strings.Contains(output.String(), "conflict  ledger: data") {
		t.Fatalf("inventory report, report: %s", output.String())
	}
}

func testLockReentry(t *testing.T) {
	t.Helper()
	first := openLoopbackMySQL(t, mysqlPort())
	second := newMySQLStore("tcp", "127.0.0.1", mysqlPort(), mysqlUser(), os.Getenv("DBHA_TEST_MYSQL_PASSWORD"))
	t.Cleanup(func() {
		_ = first.Unlock()
		_ = second.Unlock()
	})

	if err := first.Lock(); err != nil {
		t.Fatal(err)
	}
	if err := first.Lock(); err != nil {
		t.Fatalf("re-entrant lock failed, errmsg: %s", err)
	}
	if err := first.Unlock(); err != nil {
		t.Fatal(err)
	}

	started := time.Now()
	if err := second.Lock(); err != nil {
		t.Fatal(err)
	}
	if time.Since(started) > 5*time.Second {
		t.Fatal("released lock was not immediately available")
	}
}

// testLockWaitRestored checks that an ALTER restores the session lock waits it shortened.
// The values differ from the server defaults, so a reset to defaults is caught too.
func testLockWaitRestored(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	mustRun(t, Options{Type: MigrateTypeSchema}, store)
	readyQuery(t, store)
	t.Cleanup(func() { _ = store.Unlock() })

	mustExec(t, store, "SET SESSION lock_wait_timeout = 100")
	mustExec(t, store, "SET SESSION innodb_lock_wait_timeout = 60")
	if err := store.ExecDDL("ALTER TABLE `t_db_switching_log` COMMENT = 'lock wait probe'"); err != nil {
		t.Fatal(err)
	}

	lockWait := queryInt(t, store, "SELECT @@session.lock_wait_timeout")
	innodbWait := queryInt(t, store, "SELECT @@session.innodb_lock_wait_timeout")
	if lockWait != 100 || innodbWait != 60 {
		t.Fatalf("session lock wait not restored, lock_wait_timeout: %d, innodb_lock_wait_timeout: %d",
			lockWait, innodbWait)
	}
}

func mustRun(t *testing.T, opts Options, stores ...Store) {
	t.Helper()
	if err := run(opts, stores); err != nil {
		t.Fatal(err)
	}
}

func indexExists(t *testing.T, store *mysqlStore, table, name string) bool {
	t.Helper()
	count := queryInt(t, store,
		"SELECT COUNT(*) FROM information_schema.STATISTICS "+
			"WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND INDEX_NAME = ?",
		managedDatabase, table, name,
	)
	return count > 0
}

func schemaLedgerRows(t *testing.T, store *mysqlStore) int {
	t.Helper()
	return queryInt(t, store, "SELECT COUNT(*) FROM `"+schemaLedgerTable+"`")
}

func dataLedgerName(t *testing.T, store *mysqlStore) string {
	t.Helper()
	readyQuery(t, store)
	var name string
	err := store.conn.QueryRowContext(context.Background(),
		"SELECT name FROM `"+dataLedgerTable+"` WHERE version = ?", dataVersion,
	).Scan(&name)
	if err != nil {
		t.Fatal(err)
	}
	return name
}
