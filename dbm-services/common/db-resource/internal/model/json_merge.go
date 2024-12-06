/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package model

import (
	"github.com/samber/lo"
	"gorm.io/gorm/clause"
)

// JSONMergeBuilder json query expression, implements clause.Expression interface to use as querier
type JSONMergeBuilder struct {
	column string
	keys   []string
}

// Build json merge expression
// nolint
func (m *JSONMergeBuilder) Build(builder clause.Builder) {
	builder.WriteString("JSON_MERGE(")
	builder.WriteString(m.column)
	builder.WriteString(",")
	builder.WriteByte('\'')
	builder.WriteByte('[')
	for i, key := range lo.Uniq(m.keys) {
		if i > 0 {
			builder.WriteByte(',')
		}
		builder.WriteString("\"" + key + "\"")
	}
	builder.WriteByte(']')
	builder.WriteByte('\'')
	builder.WriteByte(')')
}

// JsonMerge IntArry json merge int array
func JsonMerge(column string, keys []string) *JSONMergeBuilder {
	return &JSONMergeBuilder{
		column: column,
		keys:   keys,
	}
}
