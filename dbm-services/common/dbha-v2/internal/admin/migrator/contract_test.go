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
	"reflect"
	"strings"
	"testing"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

func TestCatalogKeepsModelColumnContract(t *testing.T) {
	models := []any{
		hamodel.DbhaDataStatus{},
		hamodel.SkipDbInstance{},
		hamodel.DbmMetadata{},
		hamodel.DbSwitchingLog{},
		hamodel.DbSwitchingSnapshotLog{},
		hamodel.DbSwitchingStrategy{},
	}
	for _, model := range models {
		name := model.(interface{ TableName() string }).TableName()
		spec, ok := tableByName(name)
		if !ok {
			t.Fatalf("catalog missing table, table: %s", name)
		}
		columns, primary, indexes := gormContract(model)
		for _, column := range columns {
			if !catalogHasColumn(spec, column) {
				t.Fatalf("catalog missing column, table: %s, column: %s", name, column)
			}
		}
		if !sameCols(spec.Baseline, primary) {
			t.Fatalf(
				"baseline differs from model primary key, table: %s, baseline: %s, primary_key: %s",
				name, strings.Join(spec.Baseline, ","), strings.Join(primary, ","),
			)
		}
		for _, key := range spec.KnownPKs {
			if sameCols(key, spec.Baseline) {
				t.Fatalf("historical primary key repeats the target, table: %s", name)
			}
		}
		for _, index := range indexes {
			if !catalogHasIndex(spec, index) {
				t.Fatalf("catalog missing index, table: %s, index: %s", name, strings.Join(index.columns, ","))
			}
		}
	}
	meta, _ := tableByName(hamodel.DbmMetadataTableName)
	if !catalogHasColumn(meta, "logcial_city_name") {
		t.Fatal("historical column logcial_city_name was renamed")
	}
	skip, _ := tableByName(hamodel.SkipDbInstanceTableName)
	if sameCols(skip.Baseline, []string{"bk_cloud_id", "bk_biz_id", "instance_ip", "instance_port"}) {
		t.Fatal("instance_port was added to the skip-instance primary key")
	}
}

type modelIndex struct {
	unique  bool
	columns []string
}

func gormContract(model any) ([]string, []string, []modelIndex) {
	value := reflect.TypeOf(model)
	var columns []string
	var primary []string
	grouped := map[string]*modelIndex{}
	var order []string
	for i := 0; i < value.NumField(); i++ {
		field := value.Field(i)
		tag := field.Tag.Get("gorm")
		column := ""
		var indexName string
		unique := false
		indexed := false
		for _, part := range strings.Split(tag, ";") {
			switch {
			case strings.HasPrefix(part, "column:"):
				column = strings.TrimPrefix(part, "column:")
			case strings.HasPrefix(part, "uniqueIndex"):
				unique = true
				indexed = true
				indexName = tagName(part)
			case strings.HasPrefix(part, "index"):
				indexed = true
				indexName = tagName(part)
			}
		}
		if column == "" {
			continue
		}
		columns = append(columns, column)
		if partIs(tag, "primaryKey") {
			primary = append(primary, column)
		}
		if !indexed {
			continue
		}
		if indexName == "" {
			indexName = column
		}
		idx := grouped[indexName]
		if idx == nil {
			idx = &modelIndex{unique: unique}
			grouped[indexName] = idx
			order = append(order, indexName)
		}
		idx.columns = append(idx.columns, column)
	}
	indexes := make([]modelIndex, 0, len(order))
	for _, name := range order {
		indexes = append(indexes, *grouped[name])
	}
	return columns, primary, indexes
}

func partIs(tag, want string) bool {
	for _, part := range strings.Split(tag, ";") {
		if part == want {
			return true
		}
	}
	return false
}

func tagName(part string) string {
	_, name, ok := strings.Cut(part, ":")
	if !ok {
		return ""
	}
	name, _, _ = strings.Cut(name, ",")
	return name
}

func catalogHasColumn(spec tableSpec, name string) bool {
	for _, column := range spec.Columns {
		if column.Name == name {
			return true
		}
	}
	return false
}

func catalogHasIndex(spec tableSpec, want modelIndex) bool {
	for _, index := range spec.Indexes {
		if index.Unique == want.unique && sameCols(index.Columns, want.columns) {
			return true
		}
	}
	return false
}
