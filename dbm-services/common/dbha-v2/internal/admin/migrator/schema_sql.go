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

func (form columnForm) sqlType() string {
	switch form.DataType {
	case "varchar", "char":
		return fmt.Sprintf("%s(%d)", form.DataType, form.CharLen)
	case "bigint":
		if form.Unsigned {
			return "bigint unsigned"
		}
		return "bigint"
	default:
		return form.DataType
	}
}

func columnClause(name string, form columnForm) string {
	clause := "`" + name + "` " + form.sqlType()
	if form.Nullable {
		clause += " NULL"
	} else {
		clause += " NOT NULL"
	}
	if form.HasDefault {
		clause += " DEFAULT '" + strings.ReplaceAll(form.DefaultLiteral, "'", "''") + "'"
	}
	if form.AutoIncrement {
		clause += " AUTO_INCREMENT"
	}
	return clause
}

func createSQL(spec tableSpec) string {
	parts := make([]string, 0, len(spec.Columns))
	for _, column := range spec.Columns {
		parts = append(parts, columnClause(column.Name, column.Target))
	}
	keys := make([]string, 0, len(spec.Baseline))
	for _, name := range spec.Baseline {
		keys = append(keys, "`"+name+"`")
	}
	body := strings.Join(parts, ",") + ",PRIMARY KEY (" + strings.Join(keys, ", ") + ")"
	return "CREATE TABLE `" + spec.Name + "` (" + body + ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
}

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
