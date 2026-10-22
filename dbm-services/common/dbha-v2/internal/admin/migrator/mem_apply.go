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

import "fmt"

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

func (m *memStore) addColumn(spec tableSpec, name string) error {
	table := m.snap.Tables[spec.Name]
	if table == nil {
		return fmt.Errorf("table missing, table: %s", spec.Name)
	}
	for _, column := range spec.Columns {
		if column.Name == name {
			table.Columns[name] = column.Added.asColumn(name)
			if column.HelperIndex {
				table.Indexes = append(table.Indexes, Index{
					Name: helperIndexName(name), Columns: []string{name},
				})
			}
			return nil
		}
	}
	return fmt.Errorf("unknown column, column: %s", name)
}

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

func (m *memStore) ApplyStrategies(repair bool) error {
	if !strategyReady(m.snap) {
		return fmt.Errorf("strategy table is not ready")
	}
	empty := len(m.snap.Strategies) == 0
	plan := planDefaultStrategies(empty, strategyHits(m.snap.Strategies), repair)
	logStrategyActions(m.endpoint, plan.Actions)
	if !plan.Complete {
		return nil
	}
	if err := m.EnsureDataLedger(); err != nil {
		return err
	}
	if m.txFail {
		m.txFail = false
		return fmt.Errorf("transaction failed")
	}
	if row, ok := m.snap.Data[dataVersion]; ok && row.Name != dataName {
		return fmt.Errorf("data ledger name conflict")
	}
	for _, seed := range plan.Insert {
		m.snap.Strategies = append(m.snap.Strategies, StrategyState{
			BkBizID: seed.BkBizID, Event: seed.Event, Status: seed.Status,
			Priority: seed.Priority, UpdatedAt: "inserted",
		})
	}
	if _, ok := m.snap.Data[dataVersion]; !ok {
		m.snap.Data[dataVersion] = Ledger{Version: dataVersion, Name: dataName}
	}
	return nil
}

func strategyHits(rows []StrategyState) map[string]strategyHit {
	hits := map[string]strategyHit{}
	for _, row := range rows {
		hits[strategyIdentity(strategySeed{BkBizID: row.BkBizID, Event: row.Event})] = strategyHit{
			Found: true, Status: row.Status, Deleted: row.Deleted,
		}
	}
	return hits
}

func (m *memStore) ProbeFacts(snap *Snapshot) error {
	return nil
}

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

func (m *memStore) applyFills(plan convergePlan) {
	table := m.snap.Tables[plan.Table]
	if table == nil {
		return
	}
	if plan.FillNull != "" {
		column := table.Columns[plan.FillNull]
		column.HasNull = false
		column.NullCount = 0
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

func assignMemIDs(column *Column) {
	if !column.HasNull && column.NullCount == 0 {
		return
	}
	count := int64(column.NullCount)
	if count == 0 {
		count = 1
	}
	if column.HasNonNull {
		column.MaxID += count
	} else {
		column.MaxID = count
	}
	column.HasNull = false
	column.NullCount = 0
	column.HasNonNull = true
}

func dropNamedIndex(indexes []Index, name string) []Index {
	kept := make([]Index, 0, len(indexes))
	for _, index := range indexes {
		if index.Name != name {
			kept = append(kept, index)
		}
	}
	return kept
}
