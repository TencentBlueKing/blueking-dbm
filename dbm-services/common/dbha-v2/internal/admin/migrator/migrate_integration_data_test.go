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
	"strconv"
	"strings"
	"testing"
	"time"
	_ "time/tzdata"
)

// dstGapLiteral does not exist in America/New_York: clocks jump from 02:00 to 03:00 that day.
const dstGapLiteral = "2026-03-08 02:30:00"

// TestMySQLStrategyDataEdges covers the data step paths that moved from hand-written SQL to GORM.
func TestMySQLStrategyDataEdges(t *testing.T) {
	previous := managedDatabase
	managedDatabase = "dbha_migrate_itest"
	t.Cleanup(func() { managedDatabase = previous })
	store := openLoopbackMySQL(t, mysqlPort())
	t.Cleanup(func() { dropManaged(t, store) })

	t.Run("insert-without-id", func(t *testing.T) { testInsertWithoutID(t, store) })
	t.Run("zero-date-deleted", func(t *testing.T) { testZeroDateDeletedKept(t, store) })
	t.Run("case-insensitive-identity", func(t *testing.T) { testCaseInsensitiveIdentity(t, store) })
	t.Run("server-clock", func(t *testing.T) { testStrategyTimesFromServer(t, store) })
	t.Run("dst-gap-literal", func(t *testing.T) { testDSTGapLiteralKept(t, store) })
}

// The server NOW() literal is written back unchanged even when it falls in a DST gap of the
// migrator host time zone.
func testDSTGapLiteralKept(t *testing.T, store *mysqlStore) {
	t.Helper()
	newYork, err := time.LoadLocation("America/New_York")
	if err != nil {
		t.Fatal(err)
	}
	previous := time.Local
	time.Local = newYork
	t.Cleanup(func() { time.Local = previous })

	resetIntegration(t, store)
	if err = run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	fixed := time.Date(2026, 3, 8, 2, 30, 0, 0, time.UTC).Unix()
	mustExec(t, store, "SET SESSION time_zone = '+00:00'")
	mustExec(t, store, "SET TIMESTAMP = "+strconv.FormatInt(fixed, 10))
	if err = run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}

	mustExec(t, store, "SET SESSION time_zone = '+00:00'")
	strategies := queryInt(t, store, "SELECT COUNT(*) FROM `t_db_switching_strategy` "+
		"WHERE created_at = '"+dstGapLiteral+"' AND updated_at = '"+dstGapLiteral+"'")
	ledgers := queryInt(t, store, "SELECT COUNT(*) FROM `"+dataLedgerTable+"` "+
		"WHERE version = 1 AND applied_at = '"+dstGapLiteral+"'")
	if strategies != len(defaultStrategies()) || ledgers != 1 {
		var written string
		scanErr := store.conn.QueryRowContext(context.Background(),
			"SELECT CAST(created_at AS CHAR) FROM `t_db_switching_strategy` LIMIT 1").Scan(&written)
		t.Fatalf("server time literal was shifted, want: %s, created_at: %s, ledgers: %d, read errmsg: %v",
			dstGapLiteral, written, ledgers, scanErr)
	}
}

// A historical strategy table keyed without id must still accept the default strategies.
func testInsertWithoutID(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	mustExec(t, store, "ALTER TABLE `t_db_switching_strategy` DROP COLUMN `id`")
	if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if strategyCount(t, store) != len(defaultStrategies()) || dataLedgerRows(t, store) != 1 {
		t.Fatal("strategy table without id did not take the default rows")
	}
}

// deleted_at = '0000-00-00 00:00:00' is not NULL, so the row stays soft-deleted.
func testZeroDateDeletedKept(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	event := defaultStrategies()[0].TriggerEventName.String()
	mustExec(t, store, "SET SESSION sql_mode = ''")
	mustExec(t, store,
		"UPDATE `t_db_switching_strategy` SET deleted_at = '0000-00-00 00:00:00', priority = 3 "+
			"WHERE bk_biz_id = 0 AND trigger_event_name = ?",
		event,
	)
	mustExec(t, store, "DELETE FROM `t_db_switching_strategy` WHERE trigger_event_name <> ?", event)
	mustExec(t, store, "DROP TABLE `"+dataLedgerTable+"`")
	if err := store.Unlock(); err != nil {
		t.Fatal(err)
	}

	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !infoHas(recorded, "action: keep-deleted", event) {
		t.Fatal("zero-date deleted_at row was not kept deleted")
	}
	if strategyPriority(t, store, event) != 3 || strategyCount(t, store) != len(defaultStrategies()) {
		t.Fatal("zero-date deleted_at row was rewritten or the absent rows were not inserted")
	}
}

// Identity matching stays in MySQL, so the column collation decides it as before.
func testCaseInsensitiveIdentity(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	event := defaultStrategies()[0].TriggerEventName.String()
	mustExec(t, store,
		"UPDATE `t_db_switching_strategy` SET trigger_event_name = ?, priority = 2 "+
			"WHERE bk_biz_id = 0 AND trigger_event_name = ?",
		strings.ToUpper(event), event,
	)
	mustExec(t, store, "DELETE FROM `"+dataLedgerTable+"`")

	recorded := captureWarn(t)
	if err := run(Options{Type: MigrateTypeData, RepairMissingData: true}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if strategyCount(t, store) != len(defaultStrategies()) || infoHas(recorded, "action: repair", event) {
		t.Fatal("case-different event was not matched by the column collation")
	}
}

// Inserted rows and the data ledger take their timestamps from the server clock.
func testStrategyTimesFromServer(t *testing.T, store *mysqlStore) {
	t.Helper()
	resetIntegration(t, store)
	if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
		t.Fatal(err)
	}

	readyQuery(t, store)
	var skew int
	err := store.conn.QueryRowContext(context.Background(),
		"SELECT MAX(ABS(TIMESTAMPDIFF(SECOND, created_at, NOW()))) FROM `t_db_switching_strategy`",
	).Scan(&skew)
	if err != nil {
		t.Fatal(err)
	}
	if time.Duration(skew)*time.Second > time.Minute {
		t.Fatalf("strategy created_at is not server time, skew_seconds: %d", skew)
	}
	if strategyValue(t, store, "created_at", defaultStrategies()[0].TriggerEventName.String()) !=
		strategyTime(t, store, defaultStrategies()[0].TriggerEventName.String()) {
		t.Fatal("created_at and updated_at differ on insert")
	}
}
