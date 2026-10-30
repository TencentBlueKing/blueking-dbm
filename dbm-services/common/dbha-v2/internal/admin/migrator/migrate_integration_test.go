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
	"strconv"
	"testing"
	"time"
)

func TestMySQLMigrationMatrix(t *testing.T) {
	previous := managedDatabase
	managedDatabase = "dbha_migrate_itest"
	t.Cleanup(func() { managedDatabase = previous })
	store := openLoopbackMySQL(t, mysqlPort())
	t.Cleanup(func() {
		_ = store.connect()
		_, _ = store.conn.ExecContext(context.Background(), "DROP DATABASE IF EXISTS `dbha_migrate_itest`")
		_ = store.Unlock()
	})

	t.Run("schema", func(t *testing.T) {
		resetIntegration(t, store)
		if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
			t.Fatal(err)
		}
		first := mustLoad(t, store)
		if strategyCount(t, store) != 0 || len(first.Schema) == 0 || first.Tables[statusTable] == nil {
			t.Fatal("schema mode did not stop at structure")
		}
		if len(first.RowCounts) != 0 {
			t.Fatal("schema load scanned table counts")
		}
		if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
			t.Fatal(err)
		}
		second := mustLoad(t, store)
		if strategyCount(t, store) != 0 || len(second.Schema) != len(first.Schema) {
			t.Fatal("second schema run changed rows or the ledger")
		}
	})

	t.Run("additive-column", func(t *testing.T) {
		resetIntegration(t, store)
		if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
			t.Fatal(err)
		}
		version := columnVersion(statusTable, "probe")
		mustExec(t, store, "ALTER TABLE `t_dbha_status` DROP COLUMN `probe`")
		mustExec(t, store, "DELETE FROM `schema_migrations` WHERE version = ?", version)
		if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
			t.Fatal(err)
		}
		snap := mustLoad(t, store)
		if _, ok := snap.Tables[statusTable].Columns["probe"]; !ok {
			t.Fatal("missing probe column was not added")
		}
		applied := ledgerTime(t, store, "schema_migrations", version)
		if err := run(Options{Type: MigrateTypeSchema}, []Store{store}); err != nil {
			t.Fatal(err)
		}
		if ledgerTime(t, store, "schema_migrations", version) != applied {
			t.Fatal("second run refreshed the schema ledger")
		}
	})

	t.Run("strategy-ledger", func(t *testing.T) {
		resetIntegration(t, store)
		if err := run(Options{Type: MigrateTypeAll}, []Store{store}); err != nil {
			t.Fatal(err)
		}
		event := defaultStrategies()[0].TriggerEventName.String()
		mustExec(t, store,
			"UPDATE `t_db_switching_strategy` SET priority = 1 WHERE bk_biz_id = 0 AND trigger_event_name = ?",
			event,
		)
		before := strategyTime(t, store, event)
		mustExec(t, store, "DELETE FROM `"+dataLedgerTable+"`")
		if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
			t.Fatal(err)
		}
		if strategyTime(t, store, event) != before || strategyPriority(t, store, event) != 1 {
			t.Fatal("data run rewrote an existing strategy")
		}
		if err := run(Options{Type: MigrateTypeData}, []Store{store}); err != nil {
			t.Fatal(err)
		}
		if strategyTime(t, store, event) != before {
			t.Fatal("second data run changed updated_at")
		}
	})
}

func resetIntegration(t *testing.T, store *mysqlStore) {
	t.Helper()
	if err := store.connect(); err != nil {
		t.Fatal(err)
	}
	if _, err := store.conn.ExecContext(
		context.Background(), "DROP DATABASE IF EXISTS `dbha_migrate_itest`",
	); err != nil {
		t.Fatal(err)
	}
	_ = store.Unlock()
}

func mustLoad(t *testing.T, store *mysqlStore) *Snapshot {
	t.Helper()
	snap, err := store.Load()
	if err != nil {
		t.Fatal(err)
	}
	return snap
}

func mustExec(t *testing.T, store *mysqlStore, query string, args ...any) {
	t.Helper()
	mustExecRaw(t, store, true, query, args...)
}

func mustExecRaw(t *testing.T, store *mysqlStore, useDatabase bool, query string, args ...any) {
	t.Helper()
	if err := store.connect(); err != nil {
		t.Fatal(err)
	}
	if useDatabase {
		if err := store.useDB(); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := store.conn.ExecContext(context.Background(), query, args...); err != nil {
		t.Fatal(err)
	}
}

func columnVersion(table, column string) int64 {
	for _, step := range schemaSteps() {
		if step.Table == table && step.Column == column {
			return step.Version
		}
	}
	return 0
}

func ledgerTime(t *testing.T, store *mysqlStore, table string, version int64) string {
	t.Helper()
	readyQuery(t, store)
	var applied time.Time
	err := store.conn.QueryRowContext(
		context.Background(), "SELECT applied_at FROM `"+table+"` WHERE version = ?", version,
	).Scan(&applied)
	if err != nil {
		t.Fatal(err)
	}
	return applied.Format(time.RFC3339Nano)
}

func strategyTime(t *testing.T, store *mysqlStore, event string) string {
	t.Helper()
	return strategyValue(t, store, "updated_at", event)
}

func strategyPriority(t *testing.T, store *mysqlStore, event string) int {
	t.Helper()
	readyQuery(t, store)
	var priority int
	err := store.conn.QueryRowContext(context.Background(),
		"SELECT priority FROM `t_db_switching_strategy` WHERE bk_biz_id = 0 AND trigger_event_name = ?",
		event,
	).Scan(&priority)
	if err != nil {
		t.Fatal(err)
	}
	return priority
}

func strategyValue(t *testing.T, store *mysqlStore, column, event string) string {
	t.Helper()
	readyQuery(t, store)
	var value time.Time
	err := store.conn.QueryRowContext(context.Background(),
		"SELECT `"+column+"` FROM `t_db_switching_strategy` WHERE bk_biz_id = 0 AND trigger_event_name = ?",
		event,
	).Scan(&value)
	if err != nil {
		t.Fatal(err)
	}
	return value.Format(time.RFC3339Nano)
}

func readyQuery(t *testing.T, store *mysqlStore) {
	t.Helper()
	if err := store.connect(); err != nil {
		t.Fatal(err)
	}
	if err := store.useDB(); err != nil {
		t.Fatal(err)
	}
}

func mysqlUser() string {
	if user := os.Getenv("DBHA_TEST_MYSQL_USER"); user != "" {
		return user
	}
	return "root"
}

func mysqlPort() int {
	return envPort("DBHA_TEST_MYSQL_PORT", 3306)
}

func mysqlPortB() int {
	return envPort("DBHA_TEST_MYSQL_PORT_B", mysqlPort()+1)
}

func envPort(name string, fallback int) int {
	raw := os.Getenv(name)
	if raw == "" {
		return fallback
	}
	port, err := strconv.Atoi(raw)
	if err != nil || port < 1 || port > 65535 {
		return fallback
	}
	return port
}

func openLoopbackMySQL(t *testing.T, port int) *mysqlStore {
	t.Helper()
	store := newMySQLStore("tcp", "127.0.0.1", port, mysqlUser(), os.Getenv("DBHA_TEST_MYSQL_PASSWORD"))
	if err := store.connect(); err != nil {
		t.Fatalf("mysql is required for integration test, addr: 127.0.0.1:%d, errmsg: %s", port, err)
	}
	return store
}
