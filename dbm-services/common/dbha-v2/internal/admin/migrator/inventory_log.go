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
	"io"
	"sort"
	"strconv"
	"strings"
)

// columnPair is one "column: type" row of the full inventory.
type columnPair struct {
	Name string
	Type string
}

// inventoryRead is the endpoint that made an inventory run stop early.
type inventoryRead struct {
	endpoint string
	err      error
}

// inventory renders a read-only report for every endpoint, changing nothing.
func inventory(stores []Store, opts Options) error {
	counts := map[string]int{}
	var blocks []string
	var missing, columns, conflict bool
	var failed inventoryRead

	for _, store := range stores {
		snap, err := store.LoadInventory()
		if err != nil {
			failed = inventoryRead{endpoint: store.Endpoint(), err: err}
			break
		}
		warnLegacyKeys(store.Endpoint(), snap)
		if err = store.ProbeFacts(snap, factScope{}); err != nil {
			failed = inventoryRead{endpoint: store.Endpoint(), err: err}
			break
		}

		class, _, _ := classify(snap)
		block, gaps, adds := renderEndpoint(store.Endpoint(), snap, opts.InventoryFull)
		blocks = append(blocks, block)
		counts[class]++
		missing = missing || len(gaps) > 0
		columns = columns || len(adds) > 0
		conflict = conflict || class == classConflict
	}

	report := assembleInventoryReport(blocks, counts, missing, columns, conflict, failed)
	writeErr := writeInventoryReport(opts, report)
	if failed.err != nil {
		return fmt.Errorf("inventory failed, endpoint: %s, errmsg: %w", failed.endpoint, failed.err)
	}
	if conflict {
		return fmt.Errorf("inventory found a structural conflict")
	}

	return writeErr
}

// writeInventoryReport writes the report to the configured writer, or discards it.
func writeInventoryReport(opts Options, report string) error {
	writer := opts.Report
	if writer == nil {
		writer = io.Discard
	}

	_, err := io.WriteString(writer, report)

	return err
}

// assembleInventoryReport joins the endpoint blocks with an overview and a verdict.
func assembleInventoryReport(
	blocks []string, counts map[string]int, missing, columns, conflict bool, failed inventoryRead,
) string {
	var b strings.Builder
	b.WriteString(overviewLine(len(blocks), counts, missing, columns, conflict))
	b.WriteByte('\n')
	for _, block := range blocks {
		b.WriteByte('\n')
		b.WriteString(strings.TrimRight(block, "\n"))
		b.WriteByte('\n')
	}
	b.WriteByte('\n')

	switch {
	case failed.err != nil:
		fmt.Fprintf(&b, "result: failed, endpoint: %s, errmsg: %s\n", failed.endpoint, failed.err.Error())
	case conflict:
		b.WriteString("result: conflict\n")
	default:
		b.WriteString("result: ok\n")
	}

	return b.String()
}

// overviewLine renders the one-line summary at the top of the report.
func overviewLine(count int, counts map[string]int, missing, columns, conflict bool) string {
	changes := "none"
	var parts []string
	if missing {
		parts = append(parts, "create_tables")
	}
	if columns {
		parts = append(parts, "add_columns")
	}
	if conflict {
		parts = append(parts, "conflict")
	}
	if len(parts) > 0 {
		changes = strings.Join(parts, ", ")
	}

	return fmt.Sprintf(
		"inventory  endpoints: %d, empty: %d, partial: %d, complete: %d, conflict: %d, changes: %s",
		count, counts[classEmpty], counts[classPartial], counts[classComplete], counts[classConflict], changes,
	)
}

// renderEndpoint renders the block of one endpoint: class, conflicts, tables, and uniques.
func renderEndpoint(endpoint string, snap *Snapshot, full bool) (string, []string, []string) {
	class, _, _ := classify(snap)
	missing, columns := snapshotGaps(snap)

	var b strings.Builder
	fmt.Fprintf(&b, "endpoint  %s\n", endpoint)
	fmt.Fprintf(&b, "class: %s    version: %s    create_tables: %s    add_columns: %s\n",
		class, versionText(snap), joinedNames(missing), joinedNames(columns))
	for _, line := range conflictLines(snap) {
		fmt.Fprintf(&b, "%s\n", line)
	}
	for _, line := range summaryLines(snap) {
		fmt.Fprintf(&b, "%s\n", line)
	}
	for _, line := range allUniqueLines(snap) {
		fmt.Fprintf(&b, "%s\n", line)
	}
	if full {
		writeColumnBlocks(&b, snap)
	}

	return b.String(), missing, columns
}

// joinedNames joins names with ", ", using "-" when there is nothing to show.
func joinedNames(names []string) string {
	if len(names) == 0 {
		return "-"
	}

	return strings.Join(names, ", ")
}

// snapshotGaps lists the missing tables and missing columns of an endpoint.
func snapshotGaps(snap *Snapshot) ([]string, []string) {
	var missing []string
	var columns []string
	for _, spec := range modelTables() {
		live := liveTable(snap, spec.Name)
		if live == nil {
			missing = append(missing, spec.Name)
			continue
		}
		for _, column := range spec.Columns {
			if _, ok := live.Columns[column.Name]; !ok {
				columns = append(columns, spec.Name+"."+column.Name)
			}
		}
	}

	return missing, columns
}

// conflictLines lists every structural conflict found on an endpoint.
func conflictLines(snap *Snapshot) []string {
	if snap == nil {
		return nil
	}

	var lines []string
	if !snap.LedgerSchemaOK {
		lines = append(lines, "conflict  ledger: schema")
	}
	if !snap.LedgerDataOK {
		lines = append(lines, "conflict  ledger: data")
	}

	for _, step := range schemaSteps() {
		if !inspectStep(snap, step).Conflict {
			continue
		}
		object := conflictObject(step)
		kind := kindText(step.Kind)
		if object == "" || kind == "" || step.Table == "" {
			continue
		}
		lines = append(lines, fmt.Sprintf(
			"conflict  table: %s, kind: %s, object: %s", step.Table, kind, object,
		))
	}

	return lines
}

// conflictObject names the object a conflicting step owns.
func conflictObject(step schemaStep) string {
	switch step.Kind {
	case objectTable:
		return step.Table
	case objectColumn, objectColumnDef:
		return step.Column
	case objectIndex:
		return step.Index
	case objectPrimaryKey:
		return "primary_key"
	default:
		return ""
	}
}

// kindText renders an object kind for the inventory report.
func kindText(kind objectKind) string {
	switch kind {
	case objectTable:
		return "table"
	case objectColumn:
		return "column"
	case objectIndex:
		return "index"
	case objectColumnDef:
		return "column_def"
	case objectPrimaryKey:
		return "primary_key"
	default:
		return ""
	}
}

// summaryLines renders the aligned per-table summary of an endpoint.
func summaryLines(snap *Snapshot) []string {
	type row struct {
		table  string
		rows   string
		status string
		pk     string
	}
	rows := make([]row, 0, len(modelTables()))
	for _, spec := range modelTables() {
		live := liveTable(snap, spec.Name)
		item := row{table: spec.Name, rows: "0", status: "-", pk: "-"}
		if snap != nil && snap.RowCounts != nil {
			item.rows = strconv.FormatInt(snap.RowCounts[spec.Name], 10)
		}
		if live != nil {
			item.status = keyStatusText(keyClass(spec, live.PK))
			item.pk = strings.Join(live.PK, ", ")
			if item.pk == "" {
				item.pk = "-"
			}
		}
		rows = append(rows, item)
	}

	tableW := len("table")
	rowsW := len("rows")
	statusW := len("key_status")
	for _, item := range rows {
		tableW = max(tableW, len(item.table))
		rowsW = max(rowsW, len(item.rows))
		statusW = max(statusW, len(item.status))
	}

	lines := []string{summaryCells("table", "rows", "key_status", tableW, rowsW, statusW) + "  primary_key"}
	for _, item := range rows {
		line := summaryCells(item.table, item.rows, item.status, tableW, rowsW, statusW) + "  " + item.pk
		lines = append(lines, line)
	}

	return lines
}

// summaryCells renders the three fixed-width cells of a summary row.
func summaryCells(table, rows, status string, tableW, rowsW, statusW int) string {
	return padRight(table, tableW) + "  " + padRight(rows, rowsW) + "  " + padRight(status, statusW)
}

// keyStatusText renders a primary-key class for the inventory report.
func keyStatusText(class string) string {
	switch class {
	case keyTarget:
		return "model"
	case keyLegacy:
		return "historical"
	case keyConflict:
		return "unrecognized"
	default:
		return "-"
	}
}

// allUniqueLines lists the unique indexes of every managed table.
func allUniqueLines(snap *Snapshot) []string {
	var lines []string
	for _, spec := range modelTables() {
		lines = append(lines, uniqueLines(spec.Name, liveTable(snap, spec.Name))...)
	}

	return lines
}

// uniqueLines lists the unique secondary indexes of one table, by index name.
func uniqueLines(table string, live *Table) []string {
	if live == nil {
		return nil
	}

	var names []string
	indexes := map[string]Index{}
	for _, index := range live.Indexes {
		if index.Primary || !index.Unique {
			continue
		}
		names = append(names, index.Name)
		indexes[index.Name] = index
	}
	sort.Strings(names)

	lines := make([]string, 0, len(names))
	for _, name := range names {
		index := indexes[name]
		lines = append(lines, "unique  "+table+"  "+name+"("+strings.Join(index.Columns, ", ")+")")
	}

	return lines
}

// writeColumnBlocks writes every column of every table, used by inventory-full.
func writeColumnBlocks(b *strings.Builder, snap *Snapshot) {
	for _, spec := range modelTables() {
		pairs := columnPairs(liveTable(snap, spec.Name))
		if len(pairs) == 0 {
			continue
		}

		width := len("column")
		for _, pair := range pairs {
			width = max(width, len(pair.Name))
		}

		fmt.Fprintf(b, "\ntable: %s\n", spec.Name)
		writeAlignedColumn(b, "column", "type", width)
		for _, pair := range pairs {
			writeAlignedColumn(b, pair.Name, pair.Type, width)
		}
	}
}

// writeAlignedColumn writes one aligned "name  type" line.
func writeAlignedColumn(b *strings.Builder, name, typ string, width int) {
	fmt.Fprintf(b, "  %s  %s\n", padRight(name, width), typ)
}

// columnPairs returns the sorted columns of a table.
func columnPairs(table *Table) []columnPair {
	if table == nil || len(table.Columns) == 0 {
		return nil
	}

	names := make([]string, 0, len(table.Columns))
	for name := range table.Columns {
		names = append(names, name)
	}
	sort.Strings(names)

	pairs := make([]columnPair, 0, len(names))
	for _, name := range names {
		pairs = append(pairs, columnPair{Name: name, Type: columnTypeText(table.Columns[name])})
	}

	return pairs
}

// columnTypeText renders the declared type of a live column.
func columnTypeText(column Column) string {
	text := column.DataType
	if (text == "varchar" || text == "char") && column.CharLen > 0 {
		text = text + "(" + strconv.Itoa(column.CharLen) + ")"
	}
	if column.Unsigned && integerType(column.DataType) {
		text += " unsigned"
	}

	return text
}

// liveTable returns the live table with the given name, or nil.
func liveTable(snap *Snapshot, name string) *Table {
	if snap == nil || snap.Tables == nil {
		return nil
	}

	return snap.Tables[name]
}

// padRight pads a cell to a fixed width for aligned output.
func padRight(text string, width int) string {
	if len(text) >= width {
		return text
	}

	return text + strings.Repeat(" ", width-len(text))
}
