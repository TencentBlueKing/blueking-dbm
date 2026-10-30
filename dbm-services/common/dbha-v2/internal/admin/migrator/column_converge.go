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
	"strings"
	"sync"

	"dbm-services/common/dbha-v2/pkg/logger"
)

// relation is how a live column compares with its target definition.
type relation int

const (
	// relSatisfy means the live column already satisfies the target.
	relSatisfy relation = iota
	// relSafe means convergence can wait; the live shape is still workable.
	relSafe
	// relConflict means the live column contradicts the target.
	relConflict
)

// convergePlan is the ordered set of statements that converges one object.
type convergePlan struct {
	Statements   []string
	Table        string
	FillNull     string
	FillNullSQL  string
	FillEmpty    string
	FillEmptySQL string
	AssignColumn string
	ColumnName   string
	Column       Column
	SetColumn    bool
	AddIndex     Index
	SetIndex     bool
	DropIndex    string
	PK           []string
	SetPK        bool
}

// columnByName returns the column spec with the given name.
func columnByName(spec tableSpec, name string) columnSpec {
	for _, column := range spec.Columns {
		if column.Name == name {
			return column
		}
	}

	return columnSpec{}
}

// columnRelation compares a target column with the live column as a whole.
func columnRelation(want columnSpec, live Column) relation {
	typeRel := typeRelation(want, live)
	if typeRel == relConflict || attributeConflict(want.Target, live) {
		return relConflict
	}
	if typeRel == relSafe || attributeSafe(want.Target, live) {
		return relSafe
	}

	return relSatisfy
}

// typeRelation compares only the type part of a column.
// A live integer narrower than the target (for example int to bigint) is a conflict on purpose:
// only explicitly recognized historical shapes converge, and widening rewrites the whole table.
func typeRelation(want columnSpec, live Column) relation {
	// A historical type may stay as long as it is not the target yet.
	if matchesHistorical(want, live) && !typeEqual(want.Target, live) {
		return relSafe
	}
	if unsignedWiden(want.Target, live) {
		if live.HasNegative {
			return relConflict
		}
		return relSafe
	}
	if typeEqual(want.Target, live) || widerType(want.Target, live) || widerInteger(want.Target, live) {
		return relSatisfy
	}
	if timeType(want.Target.DataType) && timeType(live.DataType) {
		return relSatisfy
	}

	return relConflict
}

// typeEqual reports whether two column types are exactly the same.
func typeEqual(want columnForm, live Column) bool {
	if want.DataType != live.DataType || want.Unsigned != live.Unsigned {
		return false
	}
	if want.DataType == "varchar" || want.DataType == "char" {
		return want.CharLen == live.CharLen
	}

	return true
}

// widerType reports whether the live type holds more than the target type.
func widerType(want columnForm, live Column) bool {
	if (want.DataType == "varchar" || want.DataType == "char") && want.DataType == live.DataType {
		return live.CharLen > want.CharLen
	}

	wantRank, liveRank := textRank(want.DataType), textRank(live.DataType)

	return wantRank > 0 && liveRank > wantRank
}

// unsignedWiden reports whether the target adds unsigned to the same base type.
func unsignedWiden(want columnForm, live Column) bool {
	return want.Unsigned && !live.Unsigned && want.DataType == live.DataType
}

// widerInteger reports whether the live integer type is wider than the target.
func widerInteger(want columnForm, live Column) bool {
	wantRank := integerRank(want.DataType)
	liveRank := integerRank(live.DataType)
	if wantRank == 0 || liveRank == 0 || want.Unsigned != live.Unsigned {
		return false
	}

	return liveRank > wantRank
}

// integerRank orders integer types from narrowest to widest; 0 means not integer.
func integerRank(dataType string) int {
	switch dataType {
	case "tinyint":
		return 1
	case "smallint":
		return 2
	case "mediumint":
		return 3
	case "int", "integer":
		return 4
	case "bigint":
		return 5
	default:
		return 0
	}
}

// textRank orders text types from narrowest to widest; 0 means not a text type.
func textRank(dataType string) int {
	switch dataType {
	case "tinytext":
		return 1
	case "text":
		return 2
	case "mediumtext":
		return 3
	case "longtext":
		return 4
	default:
		return 0
	}
}

// matchesHistorical reports whether the live column still has a historical type.
func matchesHistorical(want columnSpec, live Column) bool {
	if want.Historical == "" {
		return false
	}

	form, err := parseSQLType(want.Historical)
	if err != nil {
		return false
	}

	return typeEqual(form, live)
}

// attributeConflict reports whether non-type attributes contradict the target.
func attributeConflict(want columnForm, live Column) bool {
	if live.AutoIncrement && !want.AutoIncrement {
		return true
	}
	if live.Unsigned && !want.Unsigned {
		return true
	}
	if live.HasDefault && !want.HasDefault && !keptLiveDefault(want, live) && !droppedTimeDefault(want, live) {
		return true
	}
	if live.HasDefault && want.HasDefault && live.DefaultLiteral != want.DefaultLiteral {
		return true
	}
	if !live.Nullable && want.Nullable && !keptLiveDefault(want, live) {
		return true
	}
	if !want.Nullable && live.Nullable && live.HasNull && !want.HasDefault && !want.AutoIncrement {
		return true
	}

	return want.Unsigned && !live.Unsigned && live.HasNegative
}

// keptLiveDefault reports whether a live timestamp default may stay untouched.
func keptLiveDefault(want columnForm, live Column) bool {
	if want.HasDefault || want.ExplicitNull || !live.HasDefault {
		return false
	}
	if !timeType(want.DataType) || !timeType(live.DataType) {
		return false
	}

	return currentTimestamp(live.DefaultLiteral)
}

// droppedTimeDefault reports whether a nullable time column must lose its live CURRENT_TIMESTAMP default.
func droppedTimeDefault(want columnForm, live Column) bool {
	if !want.ExplicitNull || !want.Nullable || !live.Nullable || !live.HasDefault {
		return false
	}

	return timeType(want.DataType) && timeType(live.DataType) && currentTimestamp(live.DefaultLiteral)
}

// droppedOnUpdate reports whether a nullable time column must lose its live ON UPDATE attribute.
func droppedOnUpdate(want columnForm, live Column) bool {
	if !want.ExplicitNull || !want.Nullable || !live.Nullable {
		return false
	}

	return timeType(want.DataType) && timeType(live.DataType) && currentTimestamp(live.OnUpdate)
}

// timeType reports whether a type is a date-time type.
func timeType(dataType string) bool {
	return dataType == "datetime" || dataType == "timestamp"
}

// currentTimestamp reports whether a literal is CURRENT_TIMESTAMP, with or without precision.
func currentTimestamp(value string) bool {
	value = strings.ToLower(strings.TrimSpace(value))
	switch value {
	case "current_timestamp", "current_timestamp()", "now()":
		return true
	}

	if !strings.HasPrefix(value, "current_timestamp(") || !strings.HasSuffix(value, ")") {
		return false
	}
	precision := value[len("current_timestamp(") : len(value)-1]
	if precision == "" {
		return false
	}
	for _, char := range precision {
		if char < '0' || char > '9' {
			return false
		}
	}

	return true
}

// keptDefaultOnce keeps the "kept default" warning to one line per column.
var keptDefaultOnce sync.Map

// warnKeptDefault logs once that a live column default is being kept.
func warnKeptDefault(table, column, literal string) {
	if _, loaded := keptDefaultOnce.LoadOrStore(table+"."+column, true); loaded {
		return
	}

	logger.Warn(
		"keep live column default, table: %s, column: %s, default: %s",
		table, column, literal,
	)
}

// attributeSafe reports whether an attribute difference may stay for now.
func attributeSafe(want columnForm, live Column) bool {
	if want.AutoIncrement && !live.AutoIncrement {
		return true
	}
	if want.Unsigned && !live.Unsigned {
		return true
	}
	if want.HasDefault && !live.HasDefault {
		return true
	}
	if droppedTimeDefault(want, live) || droppedOnUpdate(want, live) {
		return true
	}

	return !want.Nullable && live.Nullable
}

// asColumn renders a column form as a live column.
func (form columnForm) asColumn(name string) Column {
	return Column{
		Name: name, DataType: form.DataType, CharLen: form.CharLen, Unsigned: form.Unsigned,
		Nullable: form.Nullable, AutoIncrement: form.AutoIncrement,
		HasDefault: form.HasDefault, DefaultLiteral: form.DefaultLiteral, OnUpdate: form.OnUpdate,
		Charset: form.Charset, Collation: form.Collation, Comment: form.Comment,
	}
}
