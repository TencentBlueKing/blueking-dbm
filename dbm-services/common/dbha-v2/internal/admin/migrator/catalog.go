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
	"strconv"
	"strings"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

const statusTable = hamodel.DbhaDataStatusTableName

type columnForm struct {
	DataType       string
	CharLen        int
	Unsigned       bool
	Nullable       bool
	AutoIncrement  bool
	HasDefault     bool
	DefaultLiteral string
}

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

type indexSpec struct {
	Name    string
	Unique  bool
	Columns []string
	Prefix  []int
	AddSQL  string
}

type tableSpec struct {
	Name     string
	Create   string
	Columns  []columnSpec
	Indexes  []indexSpec
	Baseline []string
	KnownPKs [][]string
}

type schemaStep struct {
	Version int64
	Name    string
	Table   string
	Kind    objectKind
	Column  string
	Index   string
	Apply   string
}

func managedTables() []tableSpec {
	tables, err := reflectManagedTables()
	if err != nil {
		panic(err)
	}
	return tables
}

func statusSpec() tableSpec {
	spec, ok := tableByName(statusTable)
	if !ok {
		panic("status table is not managed")
	}
	return spec
}

func strategySpec() tableSpec {
	spec, ok := tableByName(hamodel.DbSwitchingStrategyTableName)
	if !ok {
		panic("strategy table is not managed")
	}
	return spec
}

func schemaSteps() []schemaStep {
	var steps []schemaStep
	version := int64(1)
	for _, table := range managedTables() {
		steps = append(steps, schemaStep{
			Version: version,
			Name:    stepName(version, "create_"+table.Name),
			Table:   table.Name,
			Kind:    objectTable,
			Apply:   table.Create,
		})
		version++
		for _, column := range table.Columns {
			steps = append(steps, schemaStep{
				Version: version,
				Name:    stepName(version, table.Name+"_"+column.Name),
				Table:   table.Name,
				Kind:    objectColumn,
				Column:  column.Name,
				Apply:   "ALTER TABLE `" + table.Name + "` ADD COLUMN " + column.AddSQL,
			})
			version++
		}
		for _, index := range table.Indexes {
			steps = append(steps, schemaStep{
				Version: version,
				Name:    stepName(version, table.Name+"_"+index.Name),
				Table:   table.Name,
				Kind:    objectIndex,
				Index:   index.Name,
				Apply:   index.AddSQL,
			})
			version++
		}
	}
	return append(steps, convergeSteps(version)...)
}

func stepName(version int64, name string) string {
	return fmt.Sprintf("%06d_%s", version, name)
}

func tableByName(name string) (tableSpec, bool) {
	for _, table := range managedTables() {
		if table.Name == name {
			return table, true
		}
	}
	return tableSpec{}, false
}

func col(name, family, add string) columnSpec {
	return columnSpec{Name: name, Family: family, AddSQL: add}
}

func idx(table, name string, unique bool, columns []string, prefix []int) indexSpec {
	kind := "INDEX"
	if unique {
		kind = "UNIQUE INDEX"
	}
	var parts []string
	for i, column := range columns {
		part := "`" + column + "`"
		if i < len(prefix) && prefix[i] > 0 {
			part += sprintfPrefix(prefix[i])
		}
		parts = append(parts, part)
	}
	return indexSpec{
		Name:    name,
		Unique:  unique,
		Columns: columns,
		Prefix:  prefix,
		AddSQL:  "ALTER TABLE `" + table + "` ADD " + kind + " `" + name + "` (" + strings.Join(parts, ", ") + ")",
	}
}

func sprintfPrefix(n int) string {
	return "(" + strconv.Itoa(n) + ")"
}
