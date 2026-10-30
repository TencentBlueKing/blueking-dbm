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

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// ExecDDL replays one known step's SQL onto the in-memory snapshot.
func (m *memStore) ExecDDL(sql string) error {
	if m.failDDL {
		m.failDDL = false
		return fmt.Errorf("ddl failed")
	}

	for _, step := range schemaSteps() {
		if step.Apply != sql {
			continue
		}
		m.ddl++
		m.applied = append(m.applied, sql)
		return m.applyObject(step)
	}

	return fmt.Errorf("unknown ddl")
}

// applyObject materializes the object one step owns.
func (m *memStore) applyObject(step schemaStep) error {
	spec, ok := tableByName(step.Table)
	if !ok {
		return fmt.Errorf("unknown table, table: %s", step.Table)
	}

	switch step.Kind {
	case objectTable:
		m.snap.Tables[step.Table] = tableFromSpec(spec)
	case objectColumn:
		return m.addColumn(spec, step.Column)
	case objectIndex:
		return m.addIndex(spec, step.Index)
	}

	return nil
}

// tableFromSpec materializes a managed table at its target shape.
func tableFromSpec(spec tableSpec) *Table {
	table := &Table{
		Columns: map[string]Column{},
		PK:      append([]string{}, spec.Baseline...),
	}
	for _, column := range spec.Columns {
		table.Columns[column.Name] = column.Target.asColumn(column.Name)
	}

	return table
}

// addColumn adds one column, plus its helper index when the spec asks for one.
func (m *memStore) addColumn(spec tableSpec, name string) error {
	table := m.snap.Tables[spec.Name]
	if table == nil {
		return fmt.Errorf("table missing, table: %s", spec.Name)
	}

	for _, column := range spec.Columns {
		if column.Name != name {
			continue
		}
		table.Columns[name] = column.Added.asColumn(name)
		if column.HelperIndex {
			table.Indexes = append(table.Indexes, Index{
				Name: helperIndexName(name), Columns: []string{name},
			})
		}
		return nil
	}

	return fmt.Errorf("unknown column, column: %s", name)
}

// addIndex adds one secondary index from the table spec.
func (m *memStore) addIndex(spec tableSpec, name string) error {
	table := m.snap.Tables[spec.Name]
	if table == nil {
		return fmt.Errorf("table missing, table: %s", spec.Name)
	}

	for _, index := range spec.Indexes {
		if index.Name != name {
			continue
		}
		table.Indexes = append(table.Indexes, Index{
			Name: index.Name, Unique: index.Unique, Columns: append([]string{}, index.Columns...),
			Prefix: append([]int{}, index.Prefix...),
		})
		return nil
	}

	return fmt.Errorf("unknown index, index: %s", name)
}

// RecordSchema writes one schema ledger row, rejecting name conflicts.
func (m *memStore) RecordSchema(version int64, name string) error {
	if m.failRecord {
		m.failRecord = false
		return fmt.Errorf("ledger write failed")
	}

	if row, ok := m.snap.Schema[version]; ok {
		if row.Name != name {
			return fmt.Errorf("ledger name conflict, version: %d", version)
		}
		return nil
	}

	m.snap.Schema[version] = Ledger{Version: version, Name: name}

	return nil
}

// ApplyStrategies plans and inserts the default strategies.
func (m *memStore) ApplyStrategies(repair bool) (dataApplyResult, error) {
	if !strategyReady(m.snap) {
		return dataApplyResult{}, fmt.Errorf("strategy table is not ready")
	}

	empty := len(m.strategies) == 0
	plan, err := planDefaultStrategies(empty, strategyHits(m.strategies), repair, ledgerFrom(m.snap))
	if err != nil {
		return dataApplyResult{}, err
	}
	if !plan.Complete || plan.SkipWrite {
		return dataResult(plan, false), nil
	}

	if err := m.EnsureDataLedger(); err != nil {
		return dataApplyResult{}, err
	}
	if m.txFail {
		m.txFail = false
		return dataApplyResult{}, fmt.Errorf("transaction failed")
	}
	if row, ok := m.snap.Data[dataVersion]; ok && row.Name != dataName {
		return dataApplyResult{}, fmt.Errorf("data ledger name conflict")
	}

	m.insertPlannedStrategies(plan.Insert)
	if _, ok := m.snap.Data[dataVersion]; !ok {
		m.snap.Data[dataVersion] = Ledger{Version: dataVersion, Name: dataName}
	}

	return dataResult(plan, true), nil
}

// insertPlannedStrategies appends the planned default strategies to the store.
func (m *memStore) insertPlannedStrategies(seeds []hamodel.DbSwitchingStrategy) {
	for _, seed := range seeds {
		m.strategies = append(m.strategies, StrategyState{
			BkBizID: seed.BkBizID, Event: seed.TriggerEventName.String(), Reason: int(seed.TriggerEventNameReason),
			Status: seed.Status.String(), Priority: seed.Priority, UpdatedAt: "inserted",
		})
	}
}

// strategyHits groups live strategy rows by seed identity and ranks them with the production ranking.
func strategyHits(rows []StrategyState) map[string]strategyHit {
	grouped := map[string][]strategyRow{}
	for _, row := range rows {
		id := strategyIdentity(row.BkBizID, row.Event)
		grouped[id] = append(grouped[id], strategyRow{
			Reason: row.Reason, ReasonValid: !row.ReasonNull, Status: row.Status, Deleted: row.Deleted,
		})
	}

	hits := map[string]strategyHit{}
	for _, seed := range defaultStrategies() {
		id := seedIdentity(seed)
		if live, ok := grouped[id]; ok {
			hits[id] = bestStrategyHit(live, int(seed.TriggerEventNameReason))
		}
	}

	return hits
}

// ProbeFacts records the requested scope so tests can assert on probing.
func (m *memStore) ProbeFacts(_ *Snapshot, scope factScope) error {
	m.probes = append(m.probes, scope)

	return nil
}

// ApplyConverge applies a converge plan to the in-memory snapshot.
func (m *memStore) ApplyConverge(plan convergePlan) error {
	if m.failDDL {
		m.failDDL = false
		return fmt.Errorf("ddl failed")
	}

	m.applyFills(plan)
	if m.failAfterFill {
		m.failAfterFill = false
		m.applied = append(m.applied, plan.Statements...)
		return fmt.Errorf("ddl failed")
	}

	table := m.snap.Tables[plan.Table]
	if table == nil {
		return fmt.Errorf("table missing, table: %s", plan.Table)
	}

	if plan.SetColumn {
		table.Columns[plan.ColumnName] = plan.Column
	}
	if plan.SetIndex {
		table.Indexes = append(table.Indexes, plan.AddIndex)
	}
	if plan.DropIndex != "" {
		table.Indexes = dropNamedIndex(table.Indexes, plan.DropIndex)
	}
	if plan.SetPK {
		table.PK = append([]string{}, plan.PK...)
		m.pkAlters++
	}

	m.applied = append(m.applied, plan.Statements...)
	m.ddl += len(plan.Statements)

	return nil
}

// applyFills simulates the data-fill side effects of a converge plan.
func (m *memStore) applyFills(plan convergePlan) {
	table := m.snap.Tables[plan.Table]
	if table == nil {
		return
	}

	if plan.FillNull != "" {
		column := table.Columns[plan.FillNull]
		column.HasNull = false
		table.Columns[plan.FillNull] = column
	}
	if plan.FillEmpty != "" {
		column := table.Columns[plan.FillEmpty]
		column.HasEmpty = false
		table.Columns[plan.FillEmpty] = column
	}
	if plan.AssignColumn != "" {
		column := table.Columns[plan.AssignColumn]
		assignMemIDs(&column)
		table.Columns[plan.AssignColumn] = column
	}
}

// assignMemIDs simulates backfilling generated ids into a column.
func assignMemIDs(column *Column) {
	column.HasNull = false
}

// dropNamedIndex returns the indexes without the named one.
func dropNamedIndex(indexes []Index, name string) []Index {
	kept := make([]Index, 0, len(indexes))
	for _, index := range indexes {
		if index.Name != name {
			kept = append(kept, index)
		}
	}

	return kept
}
