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
	"errors"
	"fmt"
	"os"
	"sort"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

const e2eDatabase = "dbha_migrate_e2e"

// TestMySQLMigrateEndToEnd drives the public Run entry against two loopback MySQL servers.
func TestMySQLMigrateEndToEnd(t *testing.T) {
	previousDatabase := managedDatabase
	previousStorage := config.Cfg.Storage
	managedDatabase = e2eDatabase
	primary := openLoopbackMySQL(t, mysqlPort())
	secondary := openLoopbackMySQL(t, mysqlPortB())
	t.Cleanup(func() {
		dropManaged(t, primary)
		dropManaged(t, secondary)
		managedDatabase = previousDatabase
		config.Cfg.Storage = previousStorage
	})
	requireWritable(t, primary)
	requireWritable(t, secondary)

	t.Run("lifecycle-two-servers", func(t *testing.T) { testE2ELifecycle(t, primary, secondary) })
	t.Run("split-equals-all", func(t *testing.T) { testE2ESplitEqualsAll(t, primary) })
	t.Run("inventory-readonly", func(t *testing.T) { testE2EInventory(t, primary, secondary) })
	t.Run("schema-drift-and-repair", func(t *testing.T) { testE2ESchemaDrift(t, primary) })
	t.Run("data-gap-and-repair", func(t *testing.T) { testE2EDataGap(t, primary) })
	t.Run("same-server-alias", func(t *testing.T) { testE2ESameServerAlias(t, primary) })
	t.Run("invalid-entry", testE2EInvalidEntry)
}

func testE2ELifecycle(t *testing.T, primary, secondary *mysqlStore) {
	dropManaged(t, primary)
	dropManaged(t, secondary)
	useStorage(mysqlPort(), mysqlPortB())

	mustRunPublic(t, Options{Type: MigrateTypeAll})
	first := map[string]string{}
	for _, store := range []*mysqlStore{primary, secondary} {
		assertFullyMigrated(t, store)
		first[store.Endpoint()] = endpointState(t, store)
	}

	mustRunPublic(t, Options{Type: MigrateTypeAll})
	for _, store := range []*mysqlStore{primary, secondary} {
		if endpointState(t, store) != first[store.Endpoint()] {
			t.Fatalf("second migrate changed the endpoint, endpoint: %s", store.Endpoint())
		}
	}
}

func testE2ESplitEqualsAll(t *testing.T, store *mysqlStore) {
	dropManaged(t, store)
	useStorage(mysqlPort())

	mustRunPublic(t, Options{Type: MigrateTypeSchema})
	if strategyCount(t, store) != 0 {
		t.Fatal("schema mode wrote strategies")
	}
	mustRunPublic(t, Options{Type: MigrateTypeData})
	split := endpointState(t, store)

	dropManaged(t, store)
	mustRunPublic(t, Options{Type: MigrateTypeAll})
	if all := endpointState(t, store); all != split {
		t.Fatalf("schema then data differs from all, split: %s, all: %s", split, all)
	}
}

func testE2EInventory(t *testing.T, primary, secondary *mysqlStore) {
	dropManaged(t, primary)
	dropManaged(t, secondary)
	useStorage(mysqlPort(), mysqlPortB())
	mustRunPublic(t, Options{Type: MigrateTypeAll})
	before := endpointState(t, primary) + endpointState(t, secondary)

	var brief, full bytes.Buffer
	mustRunPublic(t, Options{Inventory: true, Report: &brief})
	mustRunPublic(t, Options{InventoryFull: true, Report: &full})
	if after := endpointState(t, primary) + endpointState(t, secondary); after != before {
		t.Fatal("inventory changed an endpoint")
	}

	for _, port := range []int{mysqlPort(), mysqlPortB()} {
		header := fmt.Sprintf("endpoint  127.0.0.1:%d", port)
		if !strings.Contains(brief.String(), header) || !strings.Contains(full.String(), header) {
			t.Fatalf("inventory report missed an endpoint, endpoint: 127.0.0.1:%d", port)
		}
	}
	if strings.Contains(brief.String(), "table: "+statusTable) {
		t.Fatal("inventory printed column blocks")
	}
	if columnType(full.String(), statusTable, "machine_id") == "" {
		t.Fatalf("inventory-full did not print one column per line, report: %s", full.String())
	}
}

func testE2ESchemaDrift(t *testing.T, store *mysqlStore) {
	dropManaged(t, store)
	useStorage(mysqlPort())
	mustRunPublic(t, Options{Type: MigrateTypeAll})
	mustExec(t, store,
		"INSERT INTO `t_dbha_status` (machine_id, bk_cloud_id, db_ip, db_port, harvest_type) "+
			"VALUES ('m1', 0, '127.0.0.1', 13306, 'default')",
	)
	mustExec(t, store, "ALTER TABLE `t_dbha_status` DROP COLUMN `probe`")
	mustExec(t, store, "ALTER TABLE `t_db_switching_log` DROP INDEX `idx_level`")
	mustExec(t, store, "DROP TABLE `t_skip_dbinstance`")

	if err := Run(Options{Type: MigrateTypeAll}); err == nil {
		t.Fatal("recorded schema loss should be drift")
	}
	if schemaRestored(t, store) {
		t.Fatal("drift rebuilt a lost object without repair")
	}

	mustRunPublic(t, Options{Type: MigrateTypeAll, RepairMissing: true})
	if !schemaRestored(t, store) || statusRows(t, store) != 1 {
		t.Fatal("repair-missing did not restore every object or lost a business row")
	}
	if strategyCount(t, store) != len(defaultStrategies()) {
		t.Fatal("schema repair changed the default strategies")
	}

	var report bytes.Buffer
	mustRunPublic(t, Options{Inventory: true, Report: &report})
	fact := lineAfter(report.String(), fmt.Sprintf("endpoint  127.0.0.1:%d", mysqlPort()))
	if !strings.Contains(fact, "create_tables: -") || !strings.Contains(fact, "add_columns: -") {
		t.Fatalf("inventory still reports gaps after repair, line: %s", fact)
	}
}

func testE2EDataGap(t *testing.T, store *mysqlStore) {
	dropManaged(t, store)
	useStorage(mysqlPort())
	mustRunPublic(t, Options{Type: MigrateTypeAll})
	seeds := defaultStrategies()
	removed, softDeleted := seeds[0], seeds[1]

	mustExec(t, store,
		"DELETE FROM `t_db_switching_strategy` "+
			"WHERE bk_biz_id = ? AND trigger_event_name = ? AND trigger_event_name_reason = ?",
		removed.BkBizID, removed.TriggerEventName.String(), int(removed.TriggerEventNameReason),
	)
	mustRunPublic(t, Options{Type: MigrateTypeAll})
	if strategyCount(t, store) != len(seeds)-1 {
		t.Fatal("data step rewrote a removed strategy without repair")
	}
	mustRunPublic(t, Options{Type: MigrateTypeAll, RepairMissingData: true})
	if strategyCount(t, store) != len(seeds) {
		t.Fatal("repair-missing-data did not restore the removed strategy")
	}

	mustExec(t, store,
		"UPDATE `t_db_switching_strategy` SET status = 'deleted', deleted_at = '2020-01-02 00:00:00' "+
			"WHERE bk_biz_id = ? AND trigger_event_name = ? AND trigger_event_name_reason = ?",
		softDeleted.BkBizID, softDeleted.TriggerEventName.String(), int(softDeleted.TriggerEventNameReason),
	)
	mustRunPublic(t, Options{Type: MigrateTypeAll, RepairMissing: true})
	deleted := queryInt(t, store, "SELECT COUNT(*) FROM `t_db_switching_strategy` WHERE status = 'deleted'")
	if deleted != 1 || strategyCount(t, store) != len(seeds) {
		t.Fatal("repair-missing revived a soft-deleted strategy")
	}
}

func testE2ESameServerAlias(t *testing.T, store *mysqlStore) {
	dropManaged(t, store)
	useStorage(mysqlPort(), mysqlPort())

	mustRunPublic(t, Options{Type: MigrateTypeAll})
	if strategyCount(t, store) != len(defaultStrategies()) || dataLedgerRows(t, store) != 1 {
		t.Fatal("aliased endpoints migrated the same server twice")
	}
	mustRunPublic(t, Options{Type: MigrateTypeAll})
	if strategyCount(t, store) != len(defaultStrategies()) {
		t.Fatal("second aliased migrate duplicated strategies")
	}
}

func testE2EInvalidEntry(t *testing.T) {
	useStorage(1)
	err := Run(Options{Type: "foo"})
	if err == nil {
		t.Fatal("unknown type was accepted")
	}
	if !hasErrorCode(err, gerrors.InvalidParameter) {
		t.Fatalf("unknown type was not rejected before connecting, errmsg: %s", err)
	}

	err = Run(Options{Inventory: true, RepairMissing: true})
	if err == nil {
		t.Fatal("inventory with repair was accepted")
	}
	if !strings.Contains(err.Error(), "inventory cannot be combined with repair") {
		t.Fatalf("inventory with repair was not rejected before connecting, errmsg: %s", err)
	}

	for _, storage := range []config.StorageConfig{
		{User: mysqlUser()},
		{Endpoint: fmt.Sprintf("127.0.0.1:%d", mysqlPort())},
	} {
		config.Cfg.Storage = storage
		err = Run(Options{Type: MigrateTypeAll})
		if err == nil {
			t.Fatal("incomplete storage config was accepted")
		}
		if !hasErrorCode(err, gerrors.InvalidParameter) {
			t.Fatalf("incomplete storage config was rejected with another error, errmsg: %s", err)
		}
	}
}

// useStorage points the global storage config at loopback endpoints on the given ports.
func useStorage(ports ...int) {
	endpoints := make([]string, 0, len(ports))
	for _, port := range ports {
		endpoints = append(endpoints, fmt.Sprintf("127.0.0.1:%d", port))
	}
	config.Cfg.Storage = config.StorageConfig{
		Endpoint: strings.Join(endpoints, constant.Delimiter),
		User:     mysqlUser(),
		Password: os.Getenv("DBHA_TEST_MYSQL_PASSWORD"),
	}
}

func mustRunPublic(t *testing.T, opts Options) {
	t.Helper()
	if err := Run(opts); err != nil {
		t.Fatalf("migrate failed, errmsg: %s", err)
	}
}

// requireWritable fails fast when an earlier aborted run left the server read only.
func requireWritable(t *testing.T, store *mysqlStore) {
	t.Helper()
	if err := store.connect(); err != nil {
		t.Fatal(err)
	}
	var readOnly, superReadOnly int
	err := store.conn.QueryRowContext(context.Background(), "SELECT @@read_only, @@super_read_only").
		Scan(&readOnly, &superReadOnly)
	if err != nil {
		t.Fatal(err)
	}
	if readOnly != 0 || superReadOnly != 0 {
		t.Fatalf("endpoint is read only, reset it before the test, endpoint: %s", store.Endpoint())
	}
}

func assertFullyMigrated(t *testing.T, store *mysqlStore) {
	t.Helper()
	snap := mustLoad(t, store)
	for _, spec := range modelTables() {
		if snap.Tables[spec.Name] == nil {
			t.Fatalf("table missing after migrate, endpoint: %s, table: %s", store.Endpoint(), spec.Name)
		}
	}
	if len(snap.Schema) == 0 || dataLedgerRows(t, store) != 1 {
		t.Fatalf("ledger missing after migrate, endpoint: %s", store.Endpoint())
	}
	if strategyCount(t, store) != len(defaultStrategies()) {
		t.Fatalf("default strategies missing after migrate, endpoint: %s", store.Endpoint())
	}
}

func schemaRestored(t *testing.T, store *mysqlStore) bool {
	t.Helper()
	snap := mustLoad(t, store)
	_, hasColumn := snap.Tables[statusTable].Columns["probe"]
	return hasColumn && indexExists(t, store, "t_db_switching_log", "idx_level") &&
		snap.Tables["t_skip_dbinstance"] != nil
}

func hasErrorCode(err error, code gerrors.Code) bool {
	var coded *gerrors.Error
	return errors.As(err, &coded) && coded.Code() == int(code)
}

// endpointState renders structure, ledger sizes, and strategy rows; timestamps are left out.
func endpointState(t *testing.T, store *mysqlStore) string {
	t.Helper()
	snap := mustLoad(t, store)
	lines := []string{
		fmt.Sprintf("schema_ledger: %d", len(snap.Schema)),
		fmt.Sprintf("data_ledger: %d", len(snap.Data)),
	}
	for name, table := range snap.Tables {
		lines = append(lines, fmt.Sprintf("table: %s, pk: %v", name, table.PK))
		for _, column := range table.Columns {
			lines = append(lines, fmt.Sprintf("column: %s, %+v", name, column))
		}
		for _, index := range table.Indexes {
			lines = append(lines, fmt.Sprintf("index: %s, %+v", name, index))
		}
	}
	lines = append(lines, strategyRows(t, store)...)
	sort.Strings(lines)

	return strings.Join(lines, "\n")
}

func strategyRows(t *testing.T, store *mysqlStore) []string {
	t.Helper()
	readyQuery(t, store)
	rows, err := store.conn.QueryContext(context.Background(),
		"SELECT CONCAT_WS('|', bk_biz_id, trigger_event_name, trigger_event_name_reason, name, "+
			"IFNULL(status, ''), priority, trigger_count) FROM `t_db_switching_strategy`",
	)
	if err != nil {
		t.Fatal(err)
	}
	defer rows.Close()

	var out []string
	for rows.Next() {
		var row string
		if err = rows.Scan(&row); err != nil {
			t.Fatal(err)
		}
		out = append(out, "strategy: "+row)
	}
	if err = rows.Err(); err != nil {
		t.Fatal(err)
	}

	return out
}
