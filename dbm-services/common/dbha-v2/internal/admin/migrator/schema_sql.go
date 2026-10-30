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
)

// parseSQLType parses a SQL type such as "bigint unsigned" or "varchar(128)".
func parseSQLType(raw string) (columnForm, error) {
	raw = strings.TrimSpace(strings.ToLower(raw))
	unsigned := strings.Contains(raw, "unsigned")
	base := strings.TrimSpace(strings.ReplaceAll(raw, "unsigned", ""))

	name, length, err := splitLength(base)
	if err != nil {
		return columnForm{}, err
	}

	return columnForm{DataType: name, CharLen: length, Unsigned: unsigned}, nil
}

// splitLength splits "varchar(128)" into "varchar" and 128.
func splitLength(raw string) (string, int, error) {
	name, suffix, ok := strings.Cut(raw, "(")
	if !ok {
		return raw, 0, nil
	}

	text := strings.TrimSuffix(suffix, ")")
	length, err := strconv.Atoi(text)
	if err != nil {
		return "", 0, fmt.Errorf("invalid type length, type: %s", raw)
	}

	return name, length, nil
}

// sqlType renders the SQL type of a column form.
func (form columnForm) sqlType() string {
	switch form.DataType {
	case "varchar", "char":
		return fmt.Sprintf("%s(%d)", form.DataType, form.CharLen)
	case "tinyint", "smallint", "mediumint", "int", "integer", "bigint":
		if form.Unsigned {
			return form.DataType + " unsigned"
		}
		return form.DataType
	default:
		return form.DataType
	}
}

// columnClause renders one column definition for CREATE TABLE and ALTER TABLE.
func columnClause(name string, form columnForm) string {
	clause := "`" + name + "` " + form.sqlType()
	clause += charsetClause(form)
	if form.Nullable {
		clause += " NULL"
	} else {
		clause += " NOT NULL"
	}
	clause += defaultClause(form)
	clause += onUpdateClause(form)
	if form.AutoIncrement {
		clause += " AUTO_INCREMENT"
	}
	if form.Comment != "" {
		clause += " COMMENT '" + strings.ReplaceAll(form.Comment, "'", "''") + "'"
	}

	return clause
}

// charsetClause renders the CHARACTER SET and COLLATE parts, when set.
func charsetClause(form columnForm) string {
	clause := ""
	if identOK(form.Charset) {
		clause += " CHARACTER SET " + form.Charset
	}
	if identOK(form.Collation) {
		clause += " COLLATE " + form.Collation
	}

	return clause
}

// defaultClause renders the DEFAULT part, quoting literals that are not timestamps.
func defaultClause(form columnForm) string {
	if !form.HasDefault {
		return ""
	}
	if currentTimestamp(form.DefaultLiteral) {
		return " DEFAULT " + form.DefaultLiteral
	}

	return " DEFAULT '" + strings.ReplaceAll(form.DefaultLiteral, "'", "''") + "'"
}

// onUpdateClause renders the ON UPDATE part for timestamp columns.
func onUpdateClause(form columnForm) string {
	if !currentTimestamp(form.OnUpdate) {
		return ""
	}

	return " ON UPDATE " + form.OnUpdate
}

// identOK reports whether a value is a bare identifier safe to inline in SQL.
func identOK(value string) bool {
	if value == "" {
		return false
	}

	for _, char := range value {
		if char != '_' && (char < '0' || char > '9') && (char < 'A' || char > 'Z') && (char < 'a' || char > 'z') {
			return false
		}
	}

	return true
}

// createSQL renders the CREATE TABLE statement of a managed table.
func createSQL(spec tableSpec) string {
	if sql, ok := publishedCreateSQL(spec); ok {
		return sql
	}

	sql, _ := renderCreate(spec, func(column columnSpec) (string, bool) {
		return columnClause(column.Name, column.Target), true
	})

	return sql
}

// publishedCreateSQL renders CREATE TABLE, freezing columns that are already published.
func publishedCreateSQL(spec tableSpec) (string, bool) {
	create, found := frozenCreate(spec.Name)

	return renderCreate(spec, func(column columnSpec) (string, bool) {
		if column.Historical == "" {
			return columnClause(column.Name, column.Target), true
		}
		if !found {
			return "", false
		}
		return createColumnClause(create, column.Name)
	})
}

// renderCreate assembles CREATE TABLE from per-column clauses.
func renderCreate(spec tableSpec, clauseOf func(columnSpec) (string, bool)) (string, bool) {
	parts := make([]string, 0, len(spec.Columns))
	for _, column := range spec.Columns {
		clause, ok := clauseOf(column)
		if !ok {
			return "", false
		}
		parts = append(parts, clause)
	}

	keys := make([]string, 0, len(spec.Baseline))
	for _, name := range spec.Baseline {
		keys = append(keys, "`"+name+"`")
	}

	body := strings.Join(parts, ",") + ",PRIMARY KEY (" + strings.Join(keys, ", ") + ")"

	return "CREATE TABLE `" + spec.Name + "` (" + body + ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4", true
}

// frozenCreate returns the published CREATE TABLE statement of a table.
func frozenCreate(table string) (string, bool) {
	for _, step := range publishedSchemaSteps() {
		if step.Kind == objectTable && step.Table == table {
			return step.Apply, true
		}
	}

	return "", false
}

// createColumnClause cuts one column definition out of a generated CREATE TABLE statement.
func createColumnClause(create, column string) (string, bool) {
	start := -1
	for _, prefix := range []string{"(`", ",`"} {
		if index := strings.Index(create, prefix+column+"` "); index >= 0 {
			start = index + 1
			break
		}
	}
	if start < 0 {
		return "", false
	}

	rest := create[start:]
	end := len(rest)
	for _, marker := range []string{",`", ",PRIMARY KEY ("} {
		if index := strings.Index(rest, marker); index >= 0 && index < end {
			end = index
		}
	}
	if end == len(rest) {
		return "", false
	}

	return rest[:end], true
}

// indexAddSQL renders the ALTER TABLE statement that adds one index.
func indexAddSQL(table string, index indexSpec) string {
	kind := "INDEX"
	if index.Unique {
		kind = "UNIQUE INDEX"
	}

	parts := make([]string, 0, len(index.Columns))
	for i, column := range index.Columns {
		part := "`" + column + "`"
		if i < len(index.Prefix) && index.Prefix[i] > 0 {
			part += "(" + strconv.Itoa(index.Prefix[i]) + ")"
		}
		parts = append(parts, part)
	}

	return "ALTER TABLE `" + table + "` ADD " + kind + " `" + index.Name + "` (" +
		strings.Join(parts, ", ") + ")"
}
