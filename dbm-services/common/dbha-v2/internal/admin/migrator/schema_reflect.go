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
	"reflect"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// pkLister is implemented by models that still accept historical primary keys.
type pkLister interface {
	MigrateKnownPKs() [][]string
}

// parsedField is one struct field as the migrator understands it.
type parsedField struct {
	column         string
	primary        bool
	autoIncrement  bool
	notNull        bool
	sqlType        string
	hasDefault     bool
	defaultLiteral string
	historical     string
	emptyAsDefault bool
	indexes        []parsedIndex
}

// parsedIndex is one index declared by a field tag.
type parsedIndex struct {
	name   string
	unique bool
	length int
}

// managedModels is the single list of hamodel models the migrator owns, in catalog order.
// Heartbeat tables and t_db_black_white_list are intentionally not managed.
func managedModels() []any {
	return []any{
		hamodel.DbhaDataStatus{},
		hamodel.DbmMetadata{},
		hamodel.SkipDbInstance{},
		hamodel.DbSwitchingLog{},
		hamodel.DbSwitchingSnapshotLog{},
		hamodel.DbSwitchingStrategy{},
	}
}

// reflectManagedTables reflects every managed model into a table spec.
func reflectManagedTables() ([]tableSpec, error) {
	models := managedModels()
	tables := make([]tableSpec, 0, len(models))
	for _, model := range models {
		table, err := reflectTable(model)
		if err != nil {
			return nil, err
		}
		tables = append(tables, table)
	}

	return tables, nil
}

// reflectTable reflects one model into a table spec.
func reflectTable(model any) (tableSpec, error) {
	named, ok := model.(interface{ TableName() string })
	if !ok {
		return tableSpec{}, fmt.Errorf("managed model has no table name")
	}

	fields, err := parseFields(reflect.TypeOf(model))
	if err != nil {
		return tableSpec{}, fmt.Errorf("parse model failed, table: %s, errmsg: %s", named.TableName(), err)
	}

	spec := tableSpec{Name: named.TableName()}
	for _, field := range fields {
		column, err := field.columnSpec()
		if err != nil {
			return tableSpec{}, fmt.Errorf("column failed, table: %s, errmsg: %s", spec.Name, err)
		}
		spec.Columns = append(spec.Columns, column)
		if column.Primary {
			spec.Baseline = append(spec.Baseline, column.Name)
		}
	}

	spec.Indexes = collectIndexes(spec.Name, fields)
	spec.KnownPKs = historicalPKs(model, spec.Baseline)
	spec.Create = createSQL(spec)

	return spec, nil
}

// parseFields parses every exported field of a model struct.
func parseFields(model reflect.Type) ([]parsedField, error) {
	if model.Kind() == reflect.Pointer {
		model = model.Elem()
	}

	var fields []parsedField
	for i := 0; i < model.NumField(); i++ {
		field := model.Field(i)
		if field.PkgPath != "" {
			continue
		}
		parsed, ok, err := parseField(field)
		if err != nil {
			return nil, err
		}
		if ok {
			fields = append(fields, parsed)
		}
	}

	return fields, nil
}

// parseField parses one struct field from its gorm and migrate tags.
func parseField(field reflect.StructField) (parsedField, bool, error) {
	gormTag := field.Tag.Get("gorm")
	if gormTag == "" {
		return parsedField{}, false, nil
	}

	parsed := parsedField{}
	for _, part := range strings.Split(gormTag, ";") {
		if err := applyGormPart(&parsed, part); err != nil {
			return parsedField{}, false, err
		}
	}
	if parsed.column == "" {
		return parsedField{}, false, nil
	}

	applyMigrateTag(&parsed, field.Tag.Get("migrate"))
	if parsed.sqlType == "" {
		sqlType, err := implicitSQLType(field.Type)
		if err != nil {
			return parsedField{}, false, fmt.Errorf("column: %s, errmsg: %s", parsed.column, err)
		}
		parsed.sqlType = sqlType
	}

	return parsed, true, nil
}

// applyGormPart applies one gorm tag part to a parsed field.
// Keys compare case-insensitively like gorm does. An unknown key is an error, so gorm and the
// migrator can never silently disagree about a column definition.
func applyGormPart(parsed *parsedField, part string) error {
	part = strings.TrimSpace(part)
	if part == "" {
		return nil
	}

	key, value, _ := strings.Cut(part, ":")
	switch strings.ToLower(strings.TrimSpace(key)) {
	case "primarykey":
		parsed.primary = true
	case "autoincrement":
		parsed.autoIncrement = true
	case "not null":
		parsed.notNull = true
	case "autocreatetime", "autoupdatetime", "premarykey":
		return nil
	case "column":
		parsed.column = value
	case "type":
		parsed.sqlType = value
	case "default":
		return applyDefault(parsed, value)
	case "uniqueindex":
		return applyIndex(parsed, part, true)
	case "index":
		return applyIndex(parsed, part, false)
	default:
		return fmt.Errorf("unsupported gorm tag, part: %s", part)
	}

	return nil
}

// applyDefault stores the default literal of a column; "null" means no literal.
func applyDefault(parsed *parsedField, value string) error {
	parsed.hasDefault = true
	if value == "null" {
		parsed.defaultLiteral = ""
		return nil
	}

	parsed.defaultLiteral = value

	return nil
}

// applyIndex attaches one index declaration to a parsed field.
func applyIndex(parsed *parsedField, part string, unique bool) error {
	name, length, err := indexName(part)
	if err != nil {
		return err
	}

	parsed.indexes = append(parsed.indexes, parsedIndex{name: name, unique: unique, length: length})

	return nil
}

// indexName reads the published name and optional prefix length of an index tag.
func indexName(part string) (string, int, error) {
	_, body, ok := strings.Cut(part, ":")
	if !ok || body == "" {
		return "", 0, fmt.Errorf("index tag needs a published name")
	}

	name, opts, _ := strings.Cut(body, ",")
	if name == "" {
		return "", 0, fmt.Errorf("index tag needs a published name")
	}
	if opts == "" {
		return name, 0, nil
	}

	raw, ok := strings.CutPrefix(opts, "length:")
	if !ok {
		return "", 0, fmt.Errorf("unsupported index option, index: %s", name)
	}
	length, err := strconv.Atoi(raw)
	if err != nil {
		return "", 0, fmt.Errorf("invalid index length, index: %s", name)
	}

	return name, length, nil
}

// applyMigrateTag applies the dbha-specific migrate tag of a field.
func applyMigrateTag(parsed *parsedField, tag string) {
	for _, part := range strings.Split(tag, ";") {
		switch {
		case part == "emptyAsDefault":
			parsed.emptyAsDefault = true
		case strings.HasPrefix(part, "historical:"):
			parsed.historical = strings.TrimPrefix(part, "historical:")
		}
	}
}

// implicitSQLType maps a Go field type to its SQL type.
func implicitSQLType(field reflect.Type) (string, error) {
	for field.Kind() == reflect.Pointer {
		field = field.Elem()
	}
	if field.Name() == "JSON" {
		return "json", nil
	}

	switch field {
	case reflect.TypeOf(time.Time{}):
		return "datetime", nil
	}

	switch field.Kind() {
	case reflect.String:
		return "varchar(128)", nil
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return "bigint", nil
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return "bigint unsigned", nil
	default:
		return "", fmt.Errorf("unsupported field type, type: %s", field.String())
	}
}

// columnSpec turns a parsed field into the target and "as added" column forms.
func (field parsedField) columnSpec() (columnSpec, error) {
	target, err := parseSQLType(field.sqlType)
	if err != nil {
		return columnSpec{}, err
	}
	// varchar(0) is valid DDL but can only hold empty strings.
	if (target.DataType == "varchar" || target.DataType == "char") && target.CharLen <= 0 {
		return columnSpec{}, fmt.Errorf("type length must be positive, column: %s, type: %s", field.column, field.sqlType)
	}
	target.Nullable = !field.primary && !field.notNull
	target.AutoIncrement = field.autoIncrement
	target.HasDefault = field.hasDefault && field.defaultLiteral != ""
	target.DefaultLiteral = field.defaultLiteral
	target.ExplicitNull = field.hasDefault && field.defaultLiteral == ""

	added := field.addedForm(target)
	column := columnSpec{
		Name: field.column, Family: familyOf(target.DataType), Primary: field.primary,
		Historical: field.historical, EmptyAsDefault: field.emptyAsDefault,
		HelperIndex: field.primary && field.autoIncrement, Target: target, Added: added,
	}
	column.AddSQL = columnClause(field.column, added)
	if column.HelperIndex {
		column.AddSQL += ", ADD INDEX `" + helperIndexName(field.column) + "` (`" + field.column + "`)"
	}

	return column, nil
}

// addedForm is the shape a column takes when added to a table that already has rows.
func (field parsedField) addedForm(target columnForm) columnForm {
	// An auto-increment primary key is added exactly as the target defines it.
	if field.primary && field.autoIncrement {
		added := target
		added.Nullable = false
		added.AutoIncrement = true
		return added
	}

	// Otherwise the column starts nullable, unless a default can backfill it.
	added := target
	added.AutoIncrement = false
	if !(field.notNull && target.HasDefault) {
		added.Nullable = true
	}

	return added
}

// collectIndexes groups per-field index declarations into table indexes.
func collectIndexes(table string, fields []parsedField) []indexSpec {
	grouped := map[string]*indexSpec{}
	var order []string
	for _, field := range fields {
		for _, item := range field.indexes {
			index := grouped[item.name]
			if index == nil {
				index = &indexSpec{Name: item.name, Unique: item.unique}
				grouped[item.name] = index
				order = append(order, item.name)
			}
			index.Unique = index.Unique || item.unique
			index.Columns = append(index.Columns, field.column)
			index.Prefix = append(index.Prefix, item.length)
		}
	}
	indexes := make([]indexSpec, 0, len(order))
	for _, name := range order {
		index := *grouped[name]
		index.AddSQL = indexAddSQL(table, index)
		indexes = append(indexes, index)
	}

	return indexes
}

// historicalPKs lists the legacy primary keys a model still accepts.
func historicalPKs(model any, baseline []string) [][]string {
	lister, ok := model.(pkLister)
	if !ok {
		return nil
	}

	var keys [][]string
	for _, key := range lister.MigrateKnownPKs() {
		if sameCols(key, baseline) {
			continue
		}
		keys = append(keys, append([]string{}, key...))
	}

	return keys
}

// familyOf maps a SQL type to the family used for compatibility checks.
func familyOf(dataType string) string {
	switch dataType {
	case "varchar", "char":
		return "varchar"
	case "tinytext", "text", "mediumtext", "longtext":
		return "text"
	case "tinyint", "smallint", "mediumint", "int", "integer", "bigint":
		return "int"
	case "datetime", "timestamp", "date":
		return "datetime"
	default:
		return dataType
	}
}

// helperIndexName is the index a migrated auto-increment column is added with.
func helperIndexName(column string) string {
	return "idx_migrate_" + column
}
