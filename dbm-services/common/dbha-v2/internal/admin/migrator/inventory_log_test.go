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
	"sort"
	"strings"
	"testing"
)

func TestInventoryReportShowsSummaryWithoutColumnWall(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	table := tableFromSpec(statusSpec())
	delete(table.Columns, "agent_id")
	table.Indexes = []Index{
		{Name: "idx_agent", Unique: true, Columns: []string{"agent_id"}},
		{Name: "idx_host", Unique: false, Columns: []string{"db_ip"}},
	}
	store.snap.Tables[statusTable] = table
	store.snap.RowCounts[statusTable] = 4
	store.strategies = []StrategyState{{BkBizID: 9, Event: "custom_event", Priority: 1}}
	other := newMem("127.0.0.1:3307", Identity{ServerUUID: "u2", Hostname: "db", Port: 3307})
	var output bytes.Buffer
	recorded := captureWarn(t)
	err := run(Options{Inventory: true, Report: &output}, []Store{store, other})
	if err != nil {
		t.Fatal(err)
	}
	if store.ddl != 0 {
		t.Fatal("inventory wrote ddl")
	}
	report := output.String()
	if strings.Contains(report, "2026/") || strings.Contains(report, "custom_event") {
		t.Fatalf("report leaked a log prefix or strategy row, report: %s", report)
	}
	if !strings.Contains(report, "endpoints: 2") || !strings.Contains(report, "changes: create_tables, add_columns") {
		t.Fatalf("overview, report: %s", report)
	}
	if hasColumnBlock(report) {
		t.Fatalf("default report printed column details, report: %s", report)
	}
	fact := lineAfter(report, "endpoint  127.0.0.1:3306")
	if !strings.Contains(fact, "class: ") || !strings.Contains(fact, "    version: ") ||
		!strings.Contains(fact, "    create_tables: t_dbm_metadata, t_skip_dbinstance") ||
		!strings.Contains(fact, "    add_columns: "+statusTable+".agent_id") {
		t.Fatalf("endpoint summary, line: %s", fact)
	}
	if strings.Contains(report, "idx_host") || !strings.Contains(report, "unique  "+statusTable+"  idx_agent(agent_id)") {
		t.Fatalf("unique index section, report: %s", report)
	}
	header, statusRow := summaryPair(t, strings.Split(report, "\n"))
	if strings.Index(header, "rows") != strings.Index(statusRow, "4") {
		t.Fatalf("rows header is not left aligned, header: %s, row: %s", header, statusRow)
	}
	if strings.Index(header, "key_status") != strings.Index(statusRow, "model") {
		t.Fatalf("key status header is not left aligned, header: %s, row: %s", header, statusRow)
	}
	pkAt := strings.Index(header, "primary_key")
	if pkAt < 0 || pkAt+len("primary_key") != len(strings.TrimRight(header, " ")) {
		t.Fatalf("primary key header was padded, header: %s", header)
	}
	if strings.Index(report, "unique  ") < strings.Index(report, "primary_key") {
		t.Fatal("unique index was inserted inside the summary table")
	}
	for _, line := range recorded.infos {
		if strings.Contains(line, "endpoint  127.0.0.1:3306") || strings.Contains(line, "create_tables") {
			t.Fatalf("inventory report was written to the logger, line: %s", line)
		}
	}
}

func TestInventoryFullPrintsOneColumnPerLine(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	table := tableFromSpec(statusSpec())
	delete(table.Columns, "agent_id")
	table.Columns["zz_extra"] = Column{Name: "zz_extra", DataType: "varchar", CharLen: 16}
	store.snap.Tables[statusTable] = table
	meta, ok := tableByName("t_dbm_metadata")
	if !ok {
		t.Fatal("metadata table is not managed")
	}
	store.snap.Tables[meta.Name] = tableFromSpec(meta)
	store.snap.Tables["schema_migrations"] = ledgerTable([]string{"version", "name", "applied_at"})
	store.snap.Tables[dataLedgerTable] = ledgerTable([]string{"version", "name", "required_schema_version", "applied_at"})
	var output bytes.Buffer
	if err := run(Options{InventoryFull: true, Report: &output}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if store.ddl != 0 {
		t.Fatal("inventory-full wrote ddl")
	}
	report := output.String()
	fact := lineAfter(report, "endpoint  127.0.0.1:3306")
	if !strings.Contains(fact, "    add_columns: "+statusTable+".agent_id") {
		t.Fatalf("missing column was not kept on the summary line, line: %s", fact)
	}
	if columnType(report, statusTable, "machine_id") != "varchar(128)" ||
		columnType(report, statusTable, "sequence_id") != "bigint unsigned" ||
		columnType(report, statusTable, "zz_extra") != "varchar(16)" {
		t.Fatalf("column type text, report: %s", report)
	}
	if columnType(report, statusTable, "agent_id") != "" {
		t.Fatalf("missing column was printed in the column block, report: %s", report)
	}
	if hasColumnTitle(report, "schema_migrations") || hasColumnTitle(report, dataLedgerTable) {
		t.Fatal("full report printed a ledger table")
	}
	names := columnNames(report, statusTable)
	if len(names) == 0 || !sort.StringsAreSorted(names) {
		t.Fatalf("column names are not sorted, names: %v", names)
	}
	if !containsAll(names, "ips", "host", "report_timestamp", "zz_extra") || containsName(names, "agent_id") {
		t.Fatalf("column names, names: %v", names)
	}
	headerAt := typeColumn(report, statusTable, "column")
	for _, name := range []string{"ips", "host", "report_timestamp"} {
		if at := typeColumn(report, statusTable, name); at < 0 || at != headerAt {
			t.Fatalf("type column drifted, name: %s, header: %d, at: %d", name, headerAt, at)
		}
	}
	statusAt, metaAt := columnTitleAt(report, statusTable), columnTitleAt(report, meta.Name)
	lines := strings.Split(report, "\n")
	if statusAt < 0 || metaAt <= statusAt || lines[metaAt-1] != "" || lines[statusAt-1] != "" {
		t.Fatalf("column blocks were not separated, status: %d, metadata: %d", statusAt, metaAt)
	}
}

func TestInventoryConflictKeepsMissingObjects(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	table := tableFromSpec(statusSpec())
	table.PK = []string{"not_a_key"}
	store.snap.Tables[statusTable] = table
	store.snap.LedgerSchemaOK = false
	var output bytes.Buffer
	err := run(Options{Inventory: true, Report: &output}, []Store{store})
	if err == nil || !strings.Contains(err.Error(), "structural conflict") {
		t.Fatalf("conflict result, err: %v", err)
	}
	report := output.String()
	if !strings.Contains(report, "result: conflict") {
		t.Fatalf("result line, report: %s", report)
	}
	if !strings.Contains(report, "conflict  ledger: schema") {
		t.Fatalf("ledger conflict, report: %s", report)
	}
	if !strings.Contains(report, "conflict  table: "+statusTable+", kind: primary_key, object: primary_key") {
		t.Fatalf("primary key conflict, report: %s", report)
	}
	if !strings.Contains(report, "key_status") || !strings.Contains(report, "unrecognized") {
		t.Fatalf("unrecognized key status, report: %s", report)
	}
	if !strings.Contains(report, "t_dbm_metadata") {
		t.Fatalf("conflict report hid a missing table, report: %s", report)
	}
	if hasColumnBlock(report) {
		t.Fatal("conflict report printed a column block")
	}
	classAt := strings.Index(report, "class: ")
	conflictAt := strings.Index(report, "conflict  ledger: schema")
	summaryAt := strings.Index(report, "key_status")
	if classAt < 0 || conflictAt < classAt || summaryAt < conflictAt {
		t.Fatalf("conflict lines moved, report: %s", report)
	}
}

func TestInventoryReadFailureStopsAfterCompletedEndpoints(t *testing.T) {
	first := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	second := newMem("127.0.0.1:3307", Identity{ServerUUID: "u2", Hostname: "db", Port: 3307})
	second.failLoad = true
	var output bytes.Buffer
	err := run(Options{Inventory: true, Report: &output}, []Store{first, second})
	if err == nil || !strings.Contains(err.Error(), "endpoint: 127.0.0.1:3307") ||
		!strings.Contains(err.Error(), "load failed") {
		t.Fatalf("read failure, err: %v", err)
	}
	report := output.String()
	if !strings.Contains(report, "endpoints: 1") || strings.Contains(report, "endpoint  127.0.0.1:3307") {
		t.Fatalf("failed endpoint was included, report: %s", report)
	}
	if !strings.Contains(report, "result: failed, endpoint: 127.0.0.1:3307, errmsg: load failed") {
		t.Fatalf("failed result, report: %s", report)
	}
}

func TestInventoryLegacyKeyWarningUsesTableAndKey(t *testing.T) {
	store := newMem("127.0.0.1:3306", Identity{ServerUUID: "u1", Hostname: "db", Port: 3306})
	table := tableFromSpec(statusSpec())
	table.PK = legacyStatusKey()
	store.snap.Tables[statusTable] = table
	var output bytes.Buffer
	recorded := captureWarn(t)
	if err := run(Options{Inventory: true, Report: &output}, []Store{store}); err != nil {
		t.Fatal(err)
	}
	if !warnHas(recorded, "table: "+statusTable, "primary_key: "+strings.Join(legacyStatusKey(), ", ")) {
		t.Fatalf("legacy key warning, warnings: %v", recorded.warnings)
	}
	if !strings.Contains(output.String(), "historical") {
		t.Fatalf("historical primary key was not labeled, report: %s", output.String())
	}
}

func columnNames(report, table string) []string {
	lines := strings.Split(report, "\n")
	var names []string
	at := columnTitleAt(report, table)
	if at < 0 {
		return nil
	}
	for _, next := range lines[at+1:] {
		if next == "" || !strings.HasPrefix(next, "  ") {
			break
		}
		name := columnField(next)
		if name == "" || name == "column" {
			continue
		}
		names = append(names, name)
	}
	return names
}

func columnType(report, table, name string) string {
	at := typeColumn(report, table, name)
	if at < 0 {
		return ""
	}
	lines := strings.Split(report, "\n")
	title := columnTitleAt(report, table)
	for _, next := range lines[title+1:] {
		if next == "" || !strings.HasPrefix(next, "  ") {
			break
		}
		if columnField(next) != name {
			continue
		}
		return next[at:]
	}
	return ""
}

func typeColumn(report, table, name string) int {
	lines := strings.Split(report, "\n")
	title := columnTitleAt(report, table)
	if title < 0 {
		return -1
	}
	for _, next := range lines[title+1:] {
		if next == "" || !strings.HasPrefix(next, "  ") {
			break
		}
		if columnField(next) != name {
			continue
		}
		field := columnField(next)
		rest := strings.TrimLeft(next[2+len(field):], " ")
		return len(next) - len(rest)
	}
	return -1
}

func columnField(line string) string {
	rest := strings.TrimPrefix(line, "  ")
	name, _, _ := strings.Cut(rest, " ")
	return name
}

func columnTitleAt(report, table string) int {
	for i, line := range strings.Split(report, "\n") {
		if line == "table: "+table {
			return i
		}
	}
	return -1
}

func hasColumnTitle(report, table string) bool {
	return columnTitleAt(report, table) >= 0
}

func hasColumnBlock(report string) bool {
	for _, line := range strings.Split(report, "\n") {
		if strings.HasPrefix(line, "table: ") {
			return true
		}
	}
	return false
}

func lineAfter(report, prefix string) string {
	lines := strings.Split(report, "\n")
	for i, line := range lines {
		if line == prefix && i+1 < len(lines) {
			return lines[i+1]
		}
	}
	return ""
}

func containsAll(names []string, want ...string) bool {
	for _, name := range want {
		if !containsName(names, name) {
			return false
		}
	}
	return true
}

func containsName(names []string, want string) bool {
	for _, name := range names {
		if name == want {
			return true
		}
	}
	return false
}

func summaryPair(t *testing.T, lines []string) (string, string) {
	t.Helper()
	for i, line := range lines {
		if !strings.HasPrefix(line, "table ") || !strings.Contains(line, "key_status") {
			continue
		}
		for _, next := range lines[i+1:] {
			if strings.HasPrefix(next, statusTable+" ") {
				return line, next
			}
		}
	}
	t.Fatal("summary table was not logged")
	return "", ""
}

func warnHas(recorded *warnLog, parts ...string) bool {
	for _, line := range recorded.warnings {
		matched := true
		for _, part := range parts {
			if !strings.Contains(line, part) {
				matched = false
				break
			}
		}
		if matched {
			return true
		}
	}
	return false
}
