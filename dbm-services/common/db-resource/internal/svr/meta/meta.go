// Package meta TODO
/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
package meta

import (
	"fmt"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

// MeasureRange TODO
type MeasureRange struct {
	Min int `json:"min"`
	Max int `json:"max"`
}

type FloatMeasureRange struct {
	Min float32 `json:"min"`
	Max float32 `json:"max"`
}

// Iegal determine whether the parameter is legal
func (m MeasureRange) Iegal() bool {
	if m.IsNotEmpty() {
		return m.Max >= m.Min
	}
	return true
}

// MatchTotalStorageSize match total disk capacity
func (m *MeasureRange) MatchTotalStorageSize(db *gorm.DB) {
	m.MatchRange(db, "total_storage_cap")
}

// MatchMem match memory size range
func (m *MeasureRange) MatchMem(db *gorm.DB) {
	m.MatchRange(db, "dram_cap")
}

// MatchCpu match cpu core number range
func (m *MeasureRange) MatchCpu(db *gorm.DB) {
	m.MatchRange(db, "cpu_num")
}

// MatchRange universal range matching
func (m *MeasureRange) MatchRange(db *gorm.DB, col string) {
	switch {
	case m.Min > 0 && m.Max > 0:
		db.Where(col+" >= ? and "+col+" <= ?", m.Min, m.Max)
	case m.Max > 0 && m.Min <= 0:
		db.Where(col+" <= ?", m.Max)
	case m.Max <= 0 && m.Min > 0:
		db.Where(col+" >= ?", m.Min)
	}
}

// MatchCpuBuilder cpu builder
func (m *MeasureRange) MatchCpuBuilder() *MeasureRangeBuilder {
	return &MeasureRangeBuilder{Col: "cpu_num", MeasureRange: m}
}

// MatchMemBuilder mem builder
func (m *MeasureRange) MatchMemBuilder() *MeasureRangeBuilder {
	return &MeasureRangeBuilder{Col: "dram_cap", MeasureRange: m}
}

// MeasureRangeBuilder build range sql
type MeasureRangeBuilder struct {
	Col string
	*MeasureRange
}

// Build build orm query sql
// nolint
func (m *MeasureRangeBuilder) Build(builder clause.Builder) {
	switch {
	case m.Min > 0 && m.Max > 0:
		builder.WriteQuoted(m.Col)
		builder.WriteString(fmt.Sprintf(" >= %d AND ", m.Min))
		builder.WriteQuoted(m.Col)
		builder.WriteString(fmt.Sprintf(" <= %d ", m.Max))
	case m.Max > 0 && m.Min <= 0:
		builder.WriteQuoted(m.Col)
		builder.WriteString(fmt.Sprintf(" <= %d ", m.Max))
	case m.Max <= 0 && m.Min > 0:
		builder.WriteQuoted(m.Col)
		builder.WriteString(fmt.Sprintf(" >= %d ", m.Min))
	}
}

// IsNotEmpty is not empty
func (m MeasureRange) IsNotEmpty() bool {
	return m.Max > 0 && m.Min > 0
}

// IsEmpty is empty
func (m MeasureRange) IsEmpty() bool {
	return m.Min == 0 && m.Max == 0
}
