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

type relation int

const (
	relSatisfy relation = iota
	relSafe
	relConflict
)

type convergePlan struct {
	Statements   []string
	Table        string
	FillNull     string
	FillNullSQL  string
	FillEmpty    string
	FillEmptySQL string
	AssignColumn string
	OrderBy      []string
	ColumnName   string
	Column       Column
	SetColumn    bool
	AddIndex     Index
	SetIndex     bool
	DropIndex    string
	PK           []string
	SetPK        bool
}

func columnByName(spec tableSpec, name string) columnSpec {
	for _, column := range spec.Columns {
		if column.Name == name {
			return column
		}
	}
	return columnSpec{}
}

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

func typeRelation(want columnSpec, live Column) relation {
	if matchesHistorical(want, live) && !typeEqual(want.Target, live) {
		return relSafe
	}
	if unsignedWiden(want.Target, live) {
		if live.HasNegative {
			return relConflict
		}
		return relSafe
	}
	if typeEqual(want.Target, live) || widerType(want.Target, live) {
		return relSatisfy
	}
	return relConflict
}

func typeEqual(want columnForm, live Column) bool {
	if want.DataType != live.DataType || want.Unsigned != live.Unsigned {
		return false
	}
	if want.DataType == "varchar" || want.DataType == "char" {
		return want.CharLen == live.CharLen
	}
	return true
}

func widerType(want columnForm, live Column) bool {
	if (want.DataType == "varchar" || want.DataType == "char") && want.DataType == live.DataType {
		return live.CharLen > want.CharLen
	}
	wantRank, liveRank := textRank(want.DataType), textRank(live.DataType)
	return wantRank > 0 && liveRank > wantRank
}

func unsignedWiden(want columnForm, live Column) bool {
	return want.Unsigned && !live.Unsigned && want.DataType == live.DataType
}

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

func attributeConflict(want columnForm, live Column) bool {
	if live.AutoIncrement && !want.AutoIncrement {
		return true
	}
	if live.Unsigned && !want.Unsigned {
		return true
	}
	if live.HasDefault && !want.HasDefault {
		return true
	}
	if live.HasDefault && want.HasDefault && live.DefaultLiteral != want.DefaultLiteral {
		return true
	}
	if !live.Nullable && want.Nullable {
		return true
	}
	if !want.Nullable && live.Nullable && live.HasNull && !want.HasDefault && !want.AutoIncrement {
		return true
	}
	return want.Unsigned && !live.Unsigned && live.HasNegative
}

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
	return !want.Nullable && live.Nullable
}

func (form columnForm) asColumn(name string) Column {
	return Column{
		Name: name, DataType: form.DataType, CharLen: form.CharLen, Unsigned: form.Unsigned,
		Nullable: form.Nullable, AutoIncrement: form.AutoIncrement,
		HasDefault: form.HasDefault, DefaultLiteral: form.DefaultLiteral,
	}
}
