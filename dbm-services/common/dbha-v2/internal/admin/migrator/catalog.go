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
	"sync"
)

var (
	managedOnce  sync.Once
	managedCache []tableSpec
	managedErr   error

	stepsOnce  sync.Once
	stepsCache []schemaStep
	stepsErr   error
)

// columnForm is the physical shape of one column as the model defines it.
type columnForm struct {
	DataType       string
	CharLen        int
	Unsigned       bool
	Nullable       bool
	AutoIncrement  bool
	HasDefault     bool
	DefaultLiteral string
	ExplicitNull   bool
	OnUpdate       string
	Charset        string
	Collation      string
	Comment        string
}

// columnSpec is one column of a managed table and the SQL that adds it.
type columnSpec struct {
	Name           string
	Family         string
	AddSQL         string
	Primary        bool
	Historical     string
	EmptyAsDefault bool
	HelperIndex    bool
	Target         columnForm
	Added          columnForm
}

// indexSpec is one secondary index and the SQL that adds it.
type indexSpec struct {
	Name    string
	Unique  bool
	Columns []string
	Prefix  []int
	AddSQL  string
}

// tableSpec is the full desired definition of one managed table.
type tableSpec struct {
	Name     string
	Create   string
	Columns  []columnSpec
	Indexes  []indexSpec
	Baseline []string
	KnownPKs [][]string
}

// schemaStep is one versioned change owned by a single schema object.
type schemaStep struct {
	Version int64
	Name    string
	Table   string
	Kind    objectKind
	Column  string
	Index   string
	Apply   string
}

// managedTables returns the reflected model tables, computed once per process.
func managedTables() ([]tableSpec, error) {
	managedOnce.Do(func() {
		managedCache, managedErr = reflectManagedTables()
	})
	if managedErr != nil {
		return nil, managedErr
	}

	return managedCache, nil
}

// modelTables is managedTables for callers that cannot proceed with a broken model.
func modelTables() []tableSpec {
	tables, err := managedTables()
	if err != nil {
		panic(err)
	}

	return tables
}

// assembledSteps returns a copy of the validated, assembled steps, computed once per process.
func assembledSteps() ([]schemaStep, error) {
	stepsOnce.Do(func() {
		stepsCache, stepsErr = assembleSchemaSteps()
	})
	if stepsErr != nil {
		return nil, stepsErr
	}

	return append([]schemaStep(nil), stepsCache...), nil
}

// schemaSteps is assembledSteps for callers that cannot proceed with a broken catalog.
func schemaSteps() []schemaStep {
	steps, err := assembledSteps()
	if err != nil {
		panic(err)
	}

	return steps
}

// stepName renders the ledger name of one schema step.
func stepName(version int64, name string) string {
	return fmt.Sprintf("%06d_%s", version, name)
}

// tableByName looks up a managed table spec by table name.
func tableByName(name string) (tableSpec, bool) {
	for _, table := range modelTables() {
		if table.Name == name {
			return table, true
		}
	}

	return tableSpec{}, false
}
