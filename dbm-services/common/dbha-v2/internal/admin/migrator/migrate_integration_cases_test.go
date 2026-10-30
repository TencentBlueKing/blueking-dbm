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
	"context"
	"os"
	"strings"
	"sync"
	"testing"
)

func TestMySQLMigrateFunctions(t *testing.T) {
	previous := managedDatabase
	managedDatabase = "dbha_migrate_itest"
	t.Cleanup(func() { managedDatabase = previous })
	store := openLoopbackMySQL(t, mysqlPort())
	t.Cleanup(func() { dropManaged(t, store) })

	t.Run("string-modify", func(t *testing.T) { testStringColumnModify(t, store) })
	t.Run("partial-tables", func(t *testing.T) { testPartialTables(t, store) })
	t.Run("drift-repair", func(t *testing.T) { testDriftRepair(t, store) })
	t.Run("unique-conflict", func(t *testing.T) { testUniqueConflict(t, store) })
	t.Run("status-primary-key", func(t *testing.T) { testStatusPrimaryKey(t, store) })
	t.Run("partial-strategies", func(t *testing.T) { testPartialStrategies(t, store) })
	t.Run("soft-deleted-strategies", func(t *testing.T) { testSoftDeletedStrategies(t, store) })
	t.Run("existing-data-blocks-defaults", func(t *testing.T) { testExistingDataBlocksDefaults(t, store) })
	t.Run("data-precheck", func(t *testing.T) { testDataPrecheckWritesNothing(t, store) })
	t.Run("concurrent-lock", func(t *testing.T) { testConcurrentLock(t) })
	t.Run("read-only-endpoint", func(t *testing.T) { testReadOnlyEndpoint(t, store) })
}

func testStringColumnModify(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	mustExec(t, store, "ALTER TABLE `t_db_switching_snapshot_log` MODIFY COLUMN `result` varchar(128) NULL")
	mustExec(t, store, "ALTER TABLE `t_dbha_status` DROP PRIMARY KEY")
	mustExec(t, store, "ALTER TABLE `t_dbha_status` MODIFY COLUMN `harvest_type` varchar(32) NULL")
	mustExec(t, store,
		"ALTER TABLE `t_dbha_status` ADD PRIMARY KEY (`machine_id`, `bk_cloud_id`, `db_ip`, `db_port`)")
	mustExec(
		t, store,
		"ALTER TABLE `t_dbha_status` MODIFY COLUMN `created_at` timestamp NOT NULL "+
			"DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
	)
	resultStep := findStep(objectColumnDef, "t_db_switching_snapshot_log", "result", "")
	harvestStep := findStep(objectColumnDef, statusTable, "harvest_type", "")
	createdStep := findStep(objectColumnDef, statusTable, "created_at", "")
	mustExec(t, store, "DELETE FROM `schema_migrations` WHERE version IN (?, ?, ?)",
		resultStep.Version, harvestStep.Version, createdStep.Version)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if got := columnDataType(t, store, "t_db_switching_snapshot_log", "result"); got != "mediumtext" {
		t.Fatalf("result was not widened, data_type: %s", got)
	}
	if !columnNotNull(t, store, statusTable, "harvest_type") {
		t.Fatal("harvest_type stayed nullable")
	}
	if got := columnDataType(t, store, statusTable, "created_at"); got != "timestamp" {
		t.Fatalf("timestamp column was rewritten, data_type: %s", got)
	}
	if !strings.Contains(strings.ToLower(columnExtra(t, store, statusTable, "created_at")), "on update") {
		t.Fatal("on update was removed")
	}
}

func columnDataType(t *testing.T, store *mysqlStore, table, column string) string {
	t.Helper()
	return columnMeta(t, store, "DATA_TYPE", table, column)
}

func columnExtra(t *testing.T, store *mysqlStore, table, column string) string {
	t.Helper()
	return columnMeta(t, store, "EXTRA", table, column)
}

func columnNotNull(t *testing.T, store *mysqlStore, table, column string) bool {
	t.Helper()
	return columnMeta(t, store, "IS_NULLABLE", table, column) == "NO"
}

func columnMeta(t *testing.T, store *mysqlStore, field, table, column string) string {
	t.Helper()
	readyQuery(t, store)
	var value string
	err := store.conn.QueryRowContext(context.Background(),
		"SELECT "+field+" FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?",
		managedDatabase, table, column,
	).Scan(&value)
	if err != nil {
		t.Fatal(err)
	}
	return value
}

func testPartialTables(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	mustExec(t, store,
		"INSERT INTO `t_dbha_status` (machine_id, bk_cloud_id, db_ip, db_port, harvest_type) "+
			"VALUES ('m1', 0, '127.0.0.1', 13306, 'default')",
	)
	mustExec(t, store, "DROP TABLE `t_db_switching_log`")
	mustExec(t, store, "DELETE FROM `schema_migrations`")
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err == nil {
		t.Fatal("partial tables should fail closed")
	}
	if statusRows(t, store) != 1 {
		t.Fatal("failed precheck changed status rows")
	}
	if err := run(Options{Type: MigrateTypeSchema, RepairMissingSchema: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	snap := mustLoad(t, store)
	if statusRows(t, store) != 1 || snap.Tables["t_db_switching_log"] == nil {
		t.Fatal("repair-missing-schema did not keep the existing row and create the missing table")
	}
}

func testDriftRepair(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	mustExec(t, store, "ALTER TABLE `t_dbha_status` DROP COLUMN `probe`")
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err == nil {
		t.Fatal("recorded column loss should be drift")
	}
	if _, ok := mustLoad(t, store).Tables[statusTable].Columns["probe"]; ok {
		t.Fatal("drift recreated the column")
	}
	if err := run(Options{Type: MigrateTypeSchema, RepairMissing: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if _, ok := mustLoad(t, store).Tables[statusTable].Columns["probe"]; !ok {
		t.Fatal("repair-missing did not restore the column")
	}
	mustExec(t, store, "DROP TABLE `t_skip_dbinstance`")
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err == nil {
		t.Fatal("recorded table loss should be drift")
	}
	if mustLoad(t, store).Tables["t_skip_dbinstance"] != nil {
		t.Fatal("drift recreated the table")
	}
	if err := run(Options{Type: MigrateTypeSchema, RepairMissingSchema: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if mustLoad(t, store).Tables["t_skip_dbinstance"] == nil {
		t.Fatal("repair-missing-schema did not rebuild the table")
	}
	mustExec(t, store, "DROP TABLE `t_skip_dbinstance`")
	if err := run(Options{Type: MigrateTypeSchema, RepairMissing: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if mustLoad(t, store).Tables["t_skip_dbinstance"] == nil {
		t.Fatal("repair-missing did not rebuild the table")
	}
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
}

func testUniqueConflict(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	mustExec(t, store, "ALTER TABLE `t_db_switching_strategy` DROP INDEX `idx_name`")
	mustExec(t, store, "ALTER TABLE `t_db_switching_strategy` ADD INDEX `idx_name` (`name`, `bk_biz_id`)")
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err == nil {
		t.Fatal("unique mismatch should conflict")
	}
	if indexUnique(t, store, "t_db_switching_strategy", "idx_name") {
		t.Fatal("conflict replaced the index")
	}
}

func testStatusPrimaryKey(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	mustExec(t, store,
		"INSERT INTO `t_dbha_status` (machine_id, bk_cloud_id, db_ip, db_port, harvest_type) "+
			"VALUES ('m1', 0, '127.0.0.1', 13306, 'default')",
	)
	mustExec(t, store,
		"ALTER TABLE `t_dbha_status` DROP PRIMARY KEY, "+
			"ADD PRIMARY KEY (`machine_id`, `bk_cloud_id`, `db_ip`, `db_port`)",
	)
	mustExec(t, store, "UPDATE `t_dbha_status` SET `harvest_type` = '' WHERE `machine_id` = 'm1'")
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !sameCols(mustLoad(t, store).Tables[statusTable].PK, statusSpec().Baseline) || harvestValue(t, store) != "default" {
		t.Fatal("schema did not converge the legacy primary key or backfill harvest_type")
	}
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !sameCols(mustLoad(t, store).Tables[statusTable].PK, statusSpec().Baseline) {
		t.Fatal("second schema run changed the primary key again")
	}
}

func testPartialStrategies(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if strategyCount(t, store) != len(defaultStrategies()) || dataLedgerRows(t, store) != 1 {
		t.Fatal("empty strategy table did not insert default rows and the data ledger")
	}
	event := defaultStrategies()[0].TriggerEventName.String()
	other := defaultStrategies()[1].TriggerEventName.String()
	mustExec(t, store,
		"UPDATE `t_db_switching_strategy` SET priority = 1 WHERE bk_biz_id = 0 AND trigger_event_name = ?",
		event,
	)
	before := strategyTime(t, store, event)
	mustExec(t, store, "DELETE FROM `t_db_switching_strategy` WHERE trigger_event_name = ?", other)
	mustExec(t, store, "DROP TABLE `"+dataLedgerTable+"`")
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if strategyTime(t, store, event) != before || strategyPriority(t, store, event) != 1 {
		t.Fatal("existing strategy was rewritten")
	}
	if strategyCount(t, store) != len(defaultStrategies())-1 || dataLedgerExists(t, store) {
		t.Fatal("missing strategy was inserted or a data ledger was created")
	}
	if !infoHas(recorded, "action: skip", other) {
		t.Fatal("missing strategy did not log action: skip")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if strategyPriority(t, store, other) != 9999 || strategyCount(t, store) != len(defaultStrategies()) {
		t.Fatal("repair-missing-data did not insert only the missing row")
	}
	if strategyTime(t, store, event) != before || strategyPriority(t, store, event) != 1 {
		t.Fatal("repair-missing-data rewrote an existing strategy")
	}
}

func testSoftDeletedStrategies(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	event := defaultStrategies()[0].TriggerEventName.String()
	mustExec(t, store,
		"UPDATE `t_db_switching_strategy` SET status = 'deleted', deleted_at = '2020-01-02 00:00:00', "+
			"priority = 3, updated_at = '2020-01-01 00:00:00' "+
			"WHERE bk_biz_id = 0 AND trigger_event_name = ?",
		event,
	)
	before := strategyTime(t, store, event)
	mustExec(t, store, "DELETE FROM `t_db_switching_strategy` WHERE trigger_event_name <> ?", event)
	mustExec(t, store, "DROP TABLE `"+dataLedgerTable+"`")
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if strategyCount(t, store) != 1 || dataLedgerExists(t, store) {
		t.Fatal("soft-deleted data inserted missing rows or created a data ledger")
	}
	assertStrategyKeptDeleted(t, store, event, before)
	if !infoHas(recorded, "action: keep-deleted", event) || !infoHas(recorded, "action: skip") {
		t.Fatal("soft-deleted strategy did not log keep-deleted and skip")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if strategyCount(t, store) != len(defaultStrategies()) || dataLedgerRows(t, store) != 1 {
		t.Fatal("repair-missing-data did not insert the absent rows")
	}
	assertStrategyKeptDeleted(t, store, event, before)
}

func testExistingDataBlocksDefaults(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	mustExec(t, store,
		"INSERT INTO `t_db_switching_strategy` "+
			"(status, name, bk_biz_id, trigger_event_name, trigger_event_name_reason, priority, "+
			"created_at, updated_at) VALUES ('enabled', 'custom', 1, 'custom-event', 0, 4, NOW(), NOW())",
	)
	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if strategyCount(t, store) != 1 || dataLedgerExists(t, store) {
		t.Fatal("existing data auto inserted default rows")
	}
	if strategyPriorityFor(t, store, 1, "custom-event") != 4 || !infoHas(recorded, "action: skip") {
		t.Fatal("custom strategy changed or the skip log was missing")
	}
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if strategyCount(t, store) != len(defaultStrategies())+1 || dataLedgerRows(t, store) != 1 {
		t.Fatal("repair-missing-data did not insert the default rows beside existing data")
	}
	if strategyPriorityFor(t, store, 1, "custom-event") != 4 {
		t.Fatal("repair-missing-data rewrote the custom row")
	}
}

func testDataPrecheckWritesNothing(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	mustExec(t, store, "ALTER TABLE `t_db_switching_strategy` DROP COLUMN `trigger_count`")
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err == nil {
		t.Fatal("missing strategy column should fail data precheck")
	}
	if strategyCount(t, store) != 0 || dataLedgerExists(t, store) {
		t.Fatal("failed data precheck wrote strategies or a data ledger")
	}
}

func assertStrategyKeptDeleted(t *testing.T, store *mysqlStore, event, updated string) {
	t.Helper()
	if strategyPriority(t, store, event) != 3 || strategyTime(t, store, event) != updated {
		t.Fatal("soft-deleted strategy priority or updated_at changed")
	}
	if strategyText(t, store, "status", event) != "deleted" || strategyValue(t, store, "deleted_at", event) == "" {
		t.Fatal("soft-deleted strategy status or deleted_at changed")
	}
}

func testConcurrentLock(t *testing.T) {
	t.Helper()
	store := openLoopbackMySQL(t, mysqlPort())
	resetIntegration(t, store)
	_ = store.Unlock()
	var group sync.WaitGroup
	errs := make(chan error, 2)
	for i := 0; i < 2; i++ {
		group.Add(1)
		go func() {
			defer group.Done()
			other := newMySQLStore("tcp", "127.0.0.1", mysqlPort(), mysqlUser(), os.Getenv("DBHA_TEST_MYSQL_PASSWORD"))
			if err := other.connect(); err != nil {
				errs <- err
				return
			}
			errs <- run(Options{Type: MigrateTypeAll}, []Store{other})
			_ = other.Unlock()
		}()
	}
	group.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			t.Fatal(err)
		}
	}
	if strategyCount(t, store) != len(defaultStrategies()) {
		t.Fatal("concurrent migrate created duplicate strategies")
	}
}

func testReadOnlyEndpoint(t *testing.T, primary *mysqlStore) {
	t.Helper()
	resetIntegration(t, primary)
	_ = primary.Unlock()
	other := openLoopbackMySQL(t, mysqlPortB())
	t.Cleanup(func() {
		mustExecRaw(t, other, false, "SET GLOBAL read_only = 0")
		dropManaged(t, other)
	})
	dropManaged(t, other)
	mustExecRaw(t, other, false, "SET GLOBAL read_only = 1")
	err := run(Options{Type: MigrateTypeAll}, []Store{primary, other})
	if err == nil {
		t.Fatal("read-only endpoint should stop the batch")
	}
	if mustLoad(t, primary).Database || mustLoad(t, other).Database {
		t.Fatal("precheck failure created a database")
	}
}

func dropManaged(t *testing.T, store *mysqlStore) {
	t.Helper()
	if err := store.connect(); err != nil {
		return
	}
	_, _ = store.conn.ExecContext(context.Background(), "DROP DATABASE IF EXISTS `"+managedDatabase+"`")
	_ = store.Unlock()
}

func statusRows(t *testing.T, store *mysqlStore) int {
	t.Helper()
	return queryInt(t, store, "SELECT COUNT(*) FROM `t_dbha_status`")
}

func strategyCount(t *testing.T, store *mysqlStore) int {
	t.Helper()
	return queryInt(t, store, "SELECT COUNT(*) FROM `t_db_switching_strategy`")
}

func harvestValue(t *testing.T, store *mysqlStore) string {
	t.Helper()
	readyQuery(t, store)
	var value string
	err := store.conn.QueryRowContext(context.Background(),
		"SELECT `harvest_type` FROM `t_dbha_status` WHERE `machine_id` = 'm1'",
	).Scan(&value)
	if err != nil {
		t.Fatal(err)
	}
	return value
}

func indexUnique(t *testing.T, store *mysqlStore, table, name string) bool {
	t.Helper()
	nonUnique := queryInt(t, store,
		"SELECT NON_UNIQUE FROM information_schema.STATISTICS "+
			"WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND INDEX_NAME = ? LIMIT 1",
		managedDatabase, table, name,
	)
	return nonUnique == 0
}

func dataLedgerExists(t *testing.T, store *mysqlStore) bool {
	t.Helper()
	count := queryInt(t, store,
		"SELECT COUNT(*) FROM information_schema.TABLES "+
			"WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?",
		managedDatabase, dataLedgerTable,
	)
	return count > 0
}

func dataLedgerRows(t *testing.T, store *mysqlStore) int {
	t.Helper()
	if !dataLedgerExists(t, store) {
		return 0
	}
	return queryInt(t, store, "SELECT COUNT(*) FROM `"+dataLedgerTable+"`")
}

func strategyText(t *testing.T, store *mysqlStore, column, event string) string {
	t.Helper()
	readyQuery(t, store)
	var value string
	err := store.conn.QueryRowContext(context.Background(),
		"SELECT `"+column+"` FROM `t_db_switching_strategy` WHERE bk_biz_id = 0 AND trigger_event_name = ?",
		event,
	).Scan(&value)
	if err != nil {
		t.Fatal(err)
	}
	return value
}

func strategyPriorityFor(t *testing.T, store *mysqlStore, biz int, event string) int {
	t.Helper()
	readyQuery(t, store)
	var priority int
	err := store.conn.QueryRowContext(context.Background(),
		"SELECT priority FROM `t_db_switching_strategy` WHERE bk_biz_id = ? AND trigger_event_name = ?",
		biz, event,
	).Scan(&priority)
	if err != nil {
		t.Fatal(err)
	}
	return priority
}

func queryInt(t *testing.T, store *mysqlStore, query string, args ...any) int {
	t.Helper()
	readyQuery(t, store)
	var value int
	if err := store.conn.QueryRowContext(context.Background(), query, args...).Scan(&value); err != nil {
		t.Fatal(err)
	}
	return value
}
