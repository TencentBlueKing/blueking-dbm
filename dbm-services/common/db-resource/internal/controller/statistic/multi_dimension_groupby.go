/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package statistic 多维度聚合统计相关功能
package statistic

import (
	"fmt"
	"reflect"
	"sort"
	"strings"

	"github.com/samber/lo"

	"dbm-services/common/go-pubpkg/logger"
)

// GroupByField 分组字段定义
type GroupByField struct {
	Name     string                        // 字段名称
	KeyFunc  func(interface{}) string      // 提取分组键的函数
	SortFunc func(interface{}) interface{} // 排序键提取函数，可选
}

// AggregationFunc 聚合函数类型
type AggregationFunc func([]interface{}) interface{}

// MultiDimensionGroupBy 多维度分组聚合配置
type MultiDimensionGroupBy struct {
	Fields       []GroupByField             // 分组字段列表
	Aggregations map[string]AggregationFunc // 聚合函数映射
	SortBy       []SortField                // 排序字段
	FilterFunc   func(interface{}) bool     // 过滤函数，可选
	ResultType   reflect.Type               // 结果类型
}

// SortField 排序字段定义
type SortField struct {
	Field     string                        // 字段名
	Ascending bool                          // 是否升序
	KeyFunc   func(interface{}) interface{} // 排序键提取函数
}

// GroupResult 分组结果
type GroupResult struct {
	Keys         map[string]interface{} // 分组键值
	Count        int                    // 记录数量
	Aggregations map[string]interface{} // 聚合结果
	Data         []interface{}          // 原始数据
}

// MultiDimensionGroupByResult 多维度分组聚合结果
type MultiDimensionGroupByResult struct {
	Groups []GroupResult          `json:"groups"`
	Total  int                    `json:"total"`
	Meta   map[string]interface{} `json:"meta,omitempty"`
}

// 预定义的聚合函数
var (
	// Count 计数聚合
	Count = func(data []interface{}) interface{} {
		return len(data)
	}

	// Sum 求和聚合（适用于数值类型）
	Sum = func(data []interface{}) interface{} {
		if len(data) == 0 {
			return 0
		}

		// 尝试转换为数值类型
		switch v := data[0].(type) {
		case int:
			sum := 0
			for _, item := range data {
				if val, ok := item.(int); ok {
					sum += val
				}
			}
			return sum
		case int64:
			sum := int64(0)
			for _, item := range data {
				if val, ok := item.(int64); ok {
					sum += val
				}
			}
			return sum
		case float64:
			sum := 0.0
			for _, item := range data {
				if val, ok := item.(float64); ok {
					sum += val
				}
			}
			return sum
		default:
			logger.Warn("不支持的求和类型: %T", v)
			return 0
		}
	}

	// Avg 平均值聚合
	Avg = func(data []interface{}) interface{} {
		if len(data) == 0 {
			return 0.0
		}

		sum := Sum(data)
		switch v := sum.(type) {
		case int:
			return float64(v) / float64(len(data))
		case int64:
			return float64(v) / float64(len(data))
		case float64:
			return v / float64(len(data))
		default:
			return 0.0
		}
	}

	// Max 最大值聚合
	Max = func(data []interface{}) interface{} {
		if len(data) == 0 {
			return nil
		}

		max := data[0]
		for _, item := range data {
			if compareValues(item, max) > 0 {
				max = item
			}
		}
		return max
	}

	// Min 最小值聚合
	Min = func(data []interface{}) interface{} {
		if len(data) == 0 {
			return nil
		}

		min := data[0]
		for _, item := range data {
			if compareValues(item, min) < 0 {
				min = item
			}
		}
		return min
	}

	// First 第一个值聚合
	First = func(data []interface{}) interface{} {
		if len(data) == 0 {
			return nil
		}
		return data[0]
	}

	// Last 最后一个值聚合
	Last = func(data []interface{}) interface{} {
		if len(data) == 0 {
			return nil
		}
		return data[len(data)-1]
	}
)

// compareValues 比较两个值的大小
func compareValues(a, b interface{}) int {
	switch va := a.(type) {
	case int:
		if vb, ok := b.(int); ok {
			if va < vb {
				return -1
			} else if va > vb {
				return 1
			}
			return 0
		}
	case int64:
		if vb, ok := b.(int64); ok {
			if va < vb {
				return -1
			} else if va > vb {
				return 1
			}
			return 0
		}
	case float64:
		if vb, ok := b.(float64); ok {
			if va < vb {
				return -1
			} else if va > vb {
				return 1
			}
			return 0
		}
	case string:
		if vb, ok := b.(string); ok {
			return strings.Compare(va, vb)
		}
	}
	return 0
}

// NewMultiDimensionGroupBy 创建多维度分组聚合器
func NewMultiDimensionGroupBy() *MultiDimensionGroupBy {
	return &MultiDimensionGroupBy{
		Fields:       make([]GroupByField, 0),
		Aggregations: make(map[string]AggregationFunc),
		SortBy:       make([]SortField, 0),
	}
}

// AddGroupField 添加分组字段
func (m *MultiDimensionGroupBy) AddGroupField(name string, keyFunc func(interface{}) string) *MultiDimensionGroupBy {
	m.Fields = append(m.Fields, GroupByField{
		Name:    name,
		KeyFunc: keyFunc,
	})
	return m
}

// AddGroupFieldWithSort 添加带排序的分组字段
func (m *MultiDimensionGroupBy) AddGroupFieldWithSort(name string, keyFunc func(interface{}) string, sortFunc func(interface{}) interface{}) *MultiDimensionGroupBy {
	m.Fields = append(m.Fields, GroupByField{
		Name:     name,
		KeyFunc:  keyFunc,
		SortFunc: sortFunc,
	})
	return m
}

// AddAggregation 添加聚合函数
func (m *MultiDimensionGroupBy) AddAggregation(name string, aggFunc AggregationFunc) *MultiDimensionGroupBy {
	m.Aggregations[name] = aggFunc
	return m
}

// AddSortField 添加排序字段
func (m *MultiDimensionGroupBy) AddSortField(field string, ascending bool, keyFunc func(interface{}) interface{}) *MultiDimensionGroupBy {
	m.SortBy = append(m.SortBy, SortField{
		Field:     field,
		Ascending: ascending,
		KeyFunc:   keyFunc,
	})
	return m
}

// SetFilter 设置过滤函数
func (m *MultiDimensionGroupBy) SetFilter(filterFunc func(interface{}) bool) *MultiDimensionGroupBy {
	m.FilterFunc = filterFunc
	return m
}

// Execute 执行多维度分组聚合
func (m *MultiDimensionGroupBy) Execute(data []interface{}) (*MultiDimensionGroupByResult, error) {
	if len(m.Fields) == 0 {
		return nil, fmt.Errorf("至少需要指定一个分组字段")
	}

	// 应用过滤函数
	filteredData := data
	if m.FilterFunc != nil {
		filteredData = lo.Filter(data, func(item interface{}, _ int) bool {
			return m.FilterFunc(item)
		})
	}

	// 分组
	groupMap := make(map[string]*GroupResult)

	for _, item := range filteredData {
		// 构建分组键
		groupKey := m.buildGroupKey(item)

		// 获取或创建分组
		group, exists := groupMap[groupKey]
		if !exists {
			group = &GroupResult{
				Keys:         m.extractGroupKeys(item),
				Count:        0,
				Aggregations: make(map[string]interface{}),
				Data:         make([]interface{}, 0),
			}
			groupMap[groupKey] = group
		}

		// 添加到分组
		group.Data = append(group.Data, item)
		group.Count++
	}

	// 计算聚合
	for _, group := range groupMap {
		for name, aggFunc := range m.Aggregations {
			group.Aggregations[name] = aggFunc(group.Data)
		}
	}

	// 转换为切片
	groups := make([]GroupResult, 0, len(groupMap))
	for _, group := range groupMap {
		groups = append(groups, *group)
	}

	// 排序
	if len(m.SortBy) > 0 {
		sort.Slice(groups, func(i, j int) bool {
			return m.compareGroups(groups[i], groups[j])
		})
	}

	return &MultiDimensionGroupByResult{
		Groups: groups,
		Total:  len(groups),
		Meta: map[string]interface{}{
			"group_fields":   lo.Map(m.Fields, func(field GroupByField, _ int) string { return field.Name }),
			"aggregations":   lo.Keys(m.Aggregations),
			"original_count": len(data),
			"filtered_count": len(filteredData),
		},
	}, nil
}

// buildGroupKey 构建分组键
func (m *MultiDimensionGroupBy) buildGroupKey(item interface{}) string {
	keys := make([]string, 0, len(m.Fields))
	for _, field := range m.Fields {
		key := field.KeyFunc(item)
		keys = append(keys, key)
	}
	return strings.Join(keys, "|")
}

// extractGroupKeys 提取分组键值
func (m *MultiDimensionGroupBy) extractGroupKeys(item interface{}) map[string]interface{} {
	keys := make(map[string]interface{})
	for _, field := range m.Fields {
		key := field.KeyFunc(item)
		keys[field.Name] = key
	}
	return keys
}

// compareGroups 比较两个分组用于排序
func (m *MultiDimensionGroupBy) compareGroups(a, b GroupResult) bool {
	for _, sortField := range m.SortBy {
		var aVal, bVal interface{}

		// 从分组键中获取值
		if val, exists := a.Keys[sortField.Field]; exists {
			aVal = val
		} else {
			// 从聚合结果中获取值
			if val, exists := a.Aggregations[sortField.Field]; exists {
				aVal = val
			}
		}

		if val, exists := b.Keys[sortField.Field]; exists {
			bVal = val
		} else {
			// 从聚合结果中获取值
			if val, exists := b.Aggregations[sortField.Field]; exists {
				bVal = val
			}
		}

		// 使用自定义排序函数
		if sortField.KeyFunc != nil {
			aVal = sortField.KeyFunc(aVal)
			bVal = sortField.KeyFunc(bVal)
		}

		// 比较值
		comparison := compareValues(aVal, bVal)
		if comparison != 0 {
			if sortField.Ascending {
				return comparison < 0
			} else {
				return comparison > 0
			}
		}
	}
	return false
}

// 常用的键提取函数

// StringKeyExtractor 字符串键提取器
func StringKeyExtractor(fieldName string) func(interface{}) string {
	return func(item interface{}) string {
		// 使用反射获取字段值
		v := reflect.ValueOf(item)
		if v.Kind() == reflect.Ptr {
			v = v.Elem()
		}

		if v.Kind() == reflect.Struct {
			field := v.FieldByName(fieldName)
			if field.IsValid() && field.CanInterface() {
				return fmt.Sprintf("%v", field.Interface())
			}
		}

		// 如果是 map
		if v.Kind() == reflect.Map {
			key := reflect.ValueOf(fieldName)
			value := v.MapIndex(key)
			if value.IsValid() && value.CanInterface() {
				return fmt.Sprintf("%v", value.Interface())
			}
		}

		return ""
	}
}

// IntKeyExtractor 整数键提取器
func IntKeyExtractor(fieldName string) func(interface{}) string {
	return func(item interface{}) string {
		v := reflect.ValueOf(item)
		if v.Kind() == reflect.Ptr {
			v = v.Elem()
		}

		if v.Kind() == reflect.Struct {
			field := v.FieldByName(fieldName)
			if field.IsValid() && field.CanInterface() {
				return fmt.Sprintf("%v", field.Interface())
			}
		}

		if v.Kind() == reflect.Map {
			key := reflect.ValueOf(fieldName)
			value := v.MapIndex(key)
			if value.IsValid() && value.CanInterface() {
				return fmt.Sprintf("%v", value.Interface())
			}
		}

		return "0"
	}
}

// FloatKeyExtractor 浮点数键提取器
func FloatKeyExtractor(fieldName string) func(interface{}) string {
	return func(item interface{}) string {
		v := reflect.ValueOf(item)
		if v.Kind() == reflect.Ptr {
			v = v.Elem()
		}

		if v.Kind() == reflect.Struct {
			field := v.FieldByName(fieldName)
			if field.IsValid() && field.CanInterface() {
				return fmt.Sprintf("%.2f", field.Interface())
			}
		}

		if v.Kind() == reflect.Map {
			key := reflect.ValueOf(fieldName)
			value := v.MapIndex(key)
			if value.IsValid() && value.CanInterface() {
				return fmt.Sprintf("%.2f", value.Interface())
			}
		}

		return "0.00"
	}
}

// CustomKeyExtractor 自定义键提取器
func CustomKeyExtractor(extractor func(interface{}) string) func(interface{}) string {
	return extractor
}
