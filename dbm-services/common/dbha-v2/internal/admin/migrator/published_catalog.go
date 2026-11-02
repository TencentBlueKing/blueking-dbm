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

// stepIdentity names the object one schema step owns.
type stepIdentity struct {
	kind   objectKind
	table  string
	column string
	index  string
}

// assembleSchemaSteps returns every step to replay: published ones plus new ones.
func assembleSchemaSteps() ([]schemaStep, error) {
	if err := validatePublishedSteps(); err != nil {
		return nil, err
	}

	published := publishedSchemaSteps()
	added, err := appendedSchemaSteps(published)
	if err != nil {
		return nil, err
	}

	return orderSchemaSteps(published, added), nil
}

// validatePublishedSteps refuses a catalog whose published entries drifted from the model.
func validatePublishedSteps() error {
	tables, err := managedTables()
	if err != nil {
		return err
	}

	specs := map[string]tableSpec{}
	for _, table := range tables {
		specs[table.Name] = table
	}

	columns := publishedColumns()
	seen := map[stepIdentity]bool{}
	for _, step := range publishedSchemaSteps() {
		id := identityOf(step)
		if seen[id] {
			return publishedStepError(step, "duplicate published step")
		}
		seen[id] = true

		spec, ok := specs[step.Table]
		if !ok {
			return publishedStepError(step, "published step missing")
		}
		want, ok := expectedPublishedApply(spec, step, columns)
		if !ok {
			return publishedStepError(step, "published step missing")
		}
		if want != step.Apply {
			return publishedStepError(step, "published apply changed")
		}
	}

	return nil
}

// publishedStepError renders the standard catalog validation error.
func publishedStepError(step schemaStep, reason string) error {
	return fmt.Errorf("%s, version: %d, name: %s", reason, step.Version, step.Name)
}

// appendedSchemaSteps builds the steps for objects no published entry covers.
func appendedSchemaSteps(published []schemaStep) ([]schemaStep, error) {
	tables, err := managedTables()
	if err != nil {
		return nil, err
	}

	known := map[stepIdentity]bool{}
	version := int64(0)
	for _, step := range published {
		known[identityOf(step)] = true
		if step.Version > version {
			version = step.Version
		}
	}

	// Ordinary steps first, so tables and columns exist before convergence runs.
	var added []schemaStep
	for _, table := range tables {
		added, version = appendMissingOrdinary(added, version, known, table)
	}
	for _, table := range tables {
		added, version = appendMissingConverge(added, version, known, table)
	}

	return added, nil
}

// appendMissingOrdinary creates steps for missing tables, columns, and indexes.
func appendMissingOrdinary(
	added []schemaStep, version int64, known map[stepIdentity]bool, table tableSpec,
) ([]schemaStep, int64) {
	if !known[stepIdentity{kind: objectTable, table: table.Name}] {
		version++
		added = append(added, schemaStep{
			Version: version,
			Name:    stepName(version, "create_"+table.Name),
			Table:   table.Name,
			Kind:    objectTable,
			Apply:   table.Create,
		})
	}

	for _, column := range table.Columns {
		id := stepIdentity{kind: objectColumn, table: table.Name, column: column.Name}
		if known[id] {
			continue
		}
		version++
		added = append(added, schemaStep{
			Version: version,
			Name:    stepName(version, table.Name+"_"+column.Name),
			Table:   table.Name,
			Kind:    objectColumn,
			Column:  column.Name,
			Apply:   "ALTER TABLE `" + table.Name + "` ADD COLUMN " + column.AddSQL,
		})
	}

	for _, index := range table.Indexes {
		id := stepIdentity{kind: objectIndex, table: table.Name, index: index.Name}
		if known[id] {
			continue
		}
		version++
		added = append(added, schemaStep{
			Version: version,
			Name:    stepName(version, table.Name+"_"+index.Name),
			Table:   table.Name,
			Kind:    objectIndex,
			Index:   index.Name,
			Apply:   index.AddSQL,
		})
	}

	return added, version
}

// appendMissingConverge creates the converge steps a table does not have yet.
func appendMissingConverge(
	added []schemaStep, version int64, known map[stepIdentity]bool, table tableSpec,
) ([]schemaStep, int64) {
	for _, column := range table.Columns {
		id := stepIdentity{kind: objectColumnDef, table: table.Name, column: column.Name}
		if known[id] {
			continue
		}
		version++
		added = append(added, schemaStep{
			Version: version,
			Name:    stepName(version, table.Name+"_"+column.Name+"_definition"),
			Table:   table.Name,
			Kind:    objectColumnDef,
			Column:  column.Name,
			Apply:   "CONVERGE COLUMN `" + table.Name + "`.`" + column.Name + "`",
		})
	}

	// A table with no legacy keys never needs its primary key converged.
	if len(table.KnownPKs) == 0 || known[stepIdentity{kind: objectPrimaryKey, table: table.Name}] {
		return added, version
	}

	version++

	return append(added, schemaStep{
		Version: version,
		Name:    stepName(version, table.Name+"_primary_key"),
		Table:   table.Name,
		Kind:    objectPrimaryKey,
		Apply:   "CONVERGE PRIMARY KEY `" + table.Name + "`",
	}), version
}

// orderSchemaSteps puts every converge step after the ordinary steps.
func orderSchemaSteps(published, added []schemaStep) []schemaStep {
	ordinary := make([]schemaStep, 0, len(published)+len(added))
	converge := make([]schemaStep, 0)
	for _, step := range published {
		if convergeKind(step.Kind) {
			converge = append(converge, step)
			continue
		}
		ordinary = append(ordinary, step)
	}
	for _, step := range added {
		if convergeKind(step.Kind) {
			converge = append(converge, step)
			continue
		}
		ordinary = append(ordinary, step)
	}

	return append(ordinary, converge...)
}

// expectedPublishedApply recomputes the SQL a published step must carry.
func expectedPublishedApply(spec tableSpec, step schemaStep, columns map[string]map[string]bool) (string, bool) {
	switch step.Kind {
	case objectTable:
		sql, ok := publishedCreateSQL(publishedTable(spec, columns[spec.Name]))
		return sql, ok
	case objectColumn:
		column := columnByName(spec, step.Column)
		if column.Name == "" {
			return "", false
		}
		// Historical columns keep their frozen clause forever.
		if column.Historical != "" {
			return step.Apply, true
		}
		return "ALTER TABLE `" + spec.Name + "` ADD COLUMN " + column.AddSQL, true
	case objectIndex:
		index, ok := findIndexSpec(spec, step.Index)
		if !ok {
			return "", false
		}
		return index.AddSQL, true
	case objectColumnDef:
		if columnByName(spec, step.Column).Name == "" {
			return "", false
		}
		return "CONVERGE COLUMN `" + spec.Name + "`.`" + step.Column + "`", true
	case objectPrimaryKey:
		if len(spec.KnownPKs) == 0 {
			return "", false
		}
		return "CONVERGE PRIMARY KEY `" + spec.Name + "`", true
	default:
		return "", false
	}
}

// publishedTable narrows a spec to the columns the published entry created.
func publishedTable(spec tableSpec, columns map[string]bool) tableSpec {
	filtered := spec
	filtered.Columns = nil
	filtered.Baseline = nil
	for _, column := range spec.Columns {
		if columns[column.Name] {
			filtered.Columns = append(filtered.Columns, column)
		}
	}
	for _, name := range spec.Baseline {
		if columns[name] {
			filtered.Baseline = append(filtered.Baseline, name)
		}
	}

	return filtered
}

// publishedColumns indexes the columns each published column step created.
func publishedColumns() map[string]map[string]bool {
	columns := map[string]map[string]bool{}
	for _, step := range publishedSchemaSteps() {
		if step.Kind != objectColumn {
			continue
		}
		if columns[step.Table] == nil {
			columns[step.Table] = map[string]bool{}
		}
		columns[step.Table][step.Column] = true
	}

	return columns
}

// findIndexSpec returns the index spec with the given name.
func findIndexSpec(spec tableSpec, name string) (indexSpec, bool) {
	for _, index := range spec.Indexes {
		if index.Name == name {
			return index, true
		}
	}

	return indexSpec{}, false
}

// identityOf is the object identity of one schema step.
func identityOf(step schemaStep) stepIdentity {
	return stepIdentity{kind: step.Kind, table: step.Table, column: step.Column, index: step.Index}
}
