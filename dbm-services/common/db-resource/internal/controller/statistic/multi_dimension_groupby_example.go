/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

// Package statistic 多维度聚合使用示例
package statistic

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
)

// ResourceItem 示例数据结构
type ResourceItem struct {
	ID          int     `json:"id"`
	City        string  `json:"city"`
	DeviceClass string  `json:"device_class"`
	CPUNum      int     `json:"cpu_num"`
	Memory      int     `json:"memory"`
	DiskSize    int64   `json:"disk_size"`
	Status      string  `json:"status"`
	BizID       int     `json:"biz_id"`
	Cost        float64 `json:"cost"`
}

// ExampleMultiDimensionGroupBy 多维度分组聚合使用示例
// nolint
func ExampleMultiDimensionGroupBy() {
	// 准备测试数据
	testData := []interface{}{
		ResourceItem{ID: 1, City: "北京", DeviceClass: "C1", CPUNum: 4, Memory: 8, DiskSize: 100, Status: "active", BizID: 1001, Cost: 100.5},
		ResourceItem{ID: 2, City: "北京", DeviceClass: "C1", CPUNum: 4, Memory: 8, DiskSize: 100, Status: "active", BizID: 1001, Cost: 100.5},
		ResourceItem{ID: 3, City: "北京", DeviceClass: "C2", CPUNum: 8, Memory: 16, DiskSize: 200, Status: "active", BizID: 1001, Cost: 200.0},
		ResourceItem{ID: 4, City: "上海", DeviceClass: "C1", CPUNum: 4, Memory: 8, DiskSize: 100, Status: "active", BizID: 1002, Cost: 120.0},
		ResourceItem{ID: 5, City: "上海", DeviceClass: "C1", CPUNum: 4, Memory: 8, DiskSize: 100, Status: "inactive", BizID: 1002, Cost: 120.0},
		ResourceItem{ID: 6, City: "深圳", DeviceClass: "C3", CPUNum: 16, Memory: 32, DiskSize: 500, Status: "active", BizID: 1003, Cost: 500.0},
	}

	// 示例1: 按城市和机型分组，统计数量和成本
	logger.Info("=== 示例1: 按城市和机型分组统计 ===")
	result1 := NewMultiDimensionGroupBy().
		AddGroupField("city", StringKeyExtractor("City")).
		AddGroupField("device_class", StringKeyExtractor("DeviceClass")).
		AddAggregation("count", Count).
		AddAggregation("total_cost", func(data []interface{}) interface{} {
			sum := 0.0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					sum += resource.Cost
				}
			}
			return sum
		}).
		AddAggregation("avg_cost", func(data []interface{}) interface{} {
			sum := 0.0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					sum += resource.Cost
				}
			}
			return sum / float64(len(data))
		}).
		AddSortField("city", true, nil).
		AddSortField("count", false, nil)

	groupResult1, err := result1.Execute(testData)
	if err != nil {
		logger.Error("执行分组聚合失败: %v", err)
		return
	}

	logger.Info("分组结果: %+v", groupResult1)
	for _, group := range groupResult1.Groups {
		logger.Info("城市: %s, 机型: %s, 数量: %d, 总成本: %.2f, 平均成本: %.2f",
			group.Keys["city"], group.Keys["device_class"],
			group.Aggregations["count"], group.Aggregations["total_cost"], group.Aggregations["avg_cost"])
	}

	// 示例2: 按业务ID分组，只统计活跃状态的资源
	logger.Info("\n=== 示例2: 按业务ID分组，只统计活跃资源 ===")
	result2 := NewMultiDimensionGroupBy().
		AddGroupField("biz_id", IntKeyExtractor("BizID")).
		AddAggregation("active_count", Count).
		AddAggregation("total_cpu", func(data []interface{}) interface{} {
			sum := 0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					sum += resource.CPUNum
				}
			}
			return sum
		}).
		AddAggregation("total_memory", func(data []interface{}) interface{} {
			sum := 0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					sum += resource.Memory
				}
			}
			return sum
		}).
		SetFilter(func(item interface{}) bool {
			if resource, ok := item.(ResourceItem); ok {
				return resource.Status == "active"
			}
			return false
		}).
		AddSortField("biz_id", true, nil)

	groupResult2, err := result2.Execute(testData)
	if err != nil {
		logger.Error("执行分组聚合失败: %v", err)
		return
	}

	logger.Info("活跃资源分组结果: %+v", groupResult2)
	for _, group := range groupResult2.Groups {
		logger.Info("业务ID: %s, 活跃数量: %d, 总CPU: %d, 总内存: %d",
			group.Keys["biz_id"], group.Aggregations["active_count"],
			group.Aggregations["total_cpu"], group.Aggregations["total_memory"])
	}

	// 示例3: 自定义键提取器 - 按CPU和内存范围分组
	logger.Info("\n=== 示例3: 按CPU和内存范围分组 ===")
	result3 := NewMultiDimensionGroupBy().
		AddGroupField("cpu_range", CustomKeyExtractor(func(item interface{}) string {
			if resource, ok := item.(ResourceItem); ok {
				if resource.CPUNum <= 4 {
					return "低配置"
				} else if resource.CPUNum <= 8 {
					return "中配置"
				} else {
					return "高配置"
				}
			}
			return "未知"
		})).
		AddGroupField("memory_range", CustomKeyExtractor(func(item interface{}) string {
			if resource, ok := item.(ResourceItem); ok {
				if resource.Memory <= 8 {
					return "小内存"
				} else if resource.Memory <= 16 {
					return "中内存"
				} else {
					return "大内存"
				}
			}
			return "未知"
		})).
		AddAggregation("count", Count).
		AddAggregation("avg_disk_size", func(data []interface{}) interface{} {
			sum := int64(0)
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					sum += resource.DiskSize
				}
			}
			return float64(sum) / float64(len(data))
		}).
		AddSortField("cpu_range", true, nil).
		AddSortField("count", false, nil)

	groupResult3, err := result3.Execute(testData)
	if err != nil {
		logger.Error("执行分组聚合失败: %v", err)
		return
	}

	logger.Info("配置范围分组结果: %+v", groupResult3)
	for _, group := range groupResult3.Groups {
		logger.Info("CPU范围: %s, 内存范围: %s, 数量: %d, 平均磁盘: %.2f",
			group.Keys["cpu_range"], group.Keys["memory_range"],
			group.Aggregations["count"], group.Aggregations["avg_disk_size"])
	}
}

// ExampleWithMapData 使用Map数据的示例
func ExampleWithMapData() {
	logger.Info("\n=== 使用Map数据的示例 ===")

	// 准备Map格式的测试数据
	mapData := []interface{}{
		map[string]interface{}{"city": "北京", "type": "mysql", "count": 10, "status": "active"},
		map[string]interface{}{"city": "北京", "type": "redis", "count": 5, "status": "active"},
		map[string]interface{}{"city": "北京", "type": "mysql", "count": 8, "status": "inactive"},
		map[string]interface{}{"city": "上海", "type": "mysql", "count": 12, "status": "active"},
		map[string]interface{}{"city": "上海", "type": "redis", "count": 3, "status": "active"},
		map[string]interface{}{"city": "深圳", "type": "mongodb", "count": 6, "status": "active"},
	}

	// 按城市和类型分组，统计活跃资源数量
	result := NewMultiDimensionGroupBy().
		AddGroupField("city", func(item interface{}) string {
			if m, ok := item.(map[string]interface{}); ok {
				if city, exists := m["city"]; exists {
					return fmt.Sprintf("%v", city)
				}
			}
			return ""
		}).
		AddGroupField("type", func(item interface{}) string {
			if m, ok := item.(map[string]interface{}); ok {
				if dbType, exists := m["type"]; exists {
					return fmt.Sprintf("%v", dbType)
				}
			}
			return ""
		}).
		AddAggregation("total_count", func(data []interface{}) interface{} {
			sum := 0
			for _, item := range data {
				if m, ok := item.(map[string]interface{}); ok {
					if count, exists := m["count"]; exists {
						if c, ok := count.(int); ok {
							sum += c
						}
					}
				}
			}
			return sum
		}).
		AddAggregation("active_count", func(data []interface{}) interface{} {
			sum := 0
			for _, item := range data {
				if m, ok := item.(map[string]interface{}); ok {
					if status, exists := m["status"]; exists && status == "active" {
						if count, exists := m["count"]; exists {
							if c, ok := count.(int); ok {
								sum += c
							}
						}
					}
				}
			}
			return sum
		}).
		SetFilter(func(item interface{}) bool {
			if m, ok := item.(map[string]interface{}); ok {
				if status, exists := m["status"]; exists {
					return status == "active"
				}
			}
			return false
		}).
		AddSortField("city", true, nil).
		AddSortField("total_count", false, nil)

	groupResult, err := result.Execute(mapData)
	if err != nil {
		logger.Error("执行分组聚合失败: %v", err)
		return
	}

	logger.Info("Map数据分组结果: %+v", groupResult)
	for _, group := range groupResult.Groups {
		logger.Info("城市: %s, 类型: %s, 总数量: %d, 活跃数量: %d",
			group.Keys["city"], group.Keys["type"],
			group.Aggregations["total_count"], group.Aggregations["active_count"])
	}
}

// ExampleComplexAggregation 复杂聚合示例
// nolint
func ExampleComplexAggregation() {
	logger.Info("\n=== 复杂聚合示例 ===")

	testData := []interface{}{
		ResourceItem{ID: 1, City: "北京", DeviceClass: "C1", CPUNum: 4, Memory: 8, DiskSize: 100, Status: "active", BizID: 1001, Cost: 100.5},
		ResourceItem{ID: 2, City: "北京", DeviceClass: "C1", CPUNum: 4, Memory: 8, DiskSize: 120, Status: "active", BizID: 1001, Cost: 110.0},
		ResourceItem{ID: 3, City: "北京", DeviceClass: "C2", CPUNum: 8, Memory: 16, DiskSize: 200, Status: "active", BizID: 1001, Cost: 200.0},
		ResourceItem{ID: 4, City: "上海", DeviceClass: "C1", CPUNum: 4, Memory: 8, DiskSize: 100, Status: "active", BizID: 1002, Cost: 120.0},
		ResourceItem{ID: 5, City: "上海", DeviceClass: "C1", CPUNum: 4, Memory: 8, DiskSize: 100, Status: "inactive", BizID: 1002, Cost: 120.0},
	}

	// 按城市分组，计算各种统计指标
	result := NewMultiDimensionGroupBy().
		AddGroupField("city", StringKeyExtractor("City")).
		AddAggregation("count", Count).
		AddAggregation("total_cost", func(data []interface{}) interface{} {
			sum := 0.0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					sum += resource.Cost
				}
			}
			return sum
		}).
		AddAggregation("avg_cost", func(data []interface{}) interface{} {
			sum := 0.0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					sum += resource.Cost
				}
			}
			return sum / float64(len(data))
		}).
		AddAggregation("max_cost", func(data []interface{}) interface{} {
			max := 0.0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					if resource.Cost > max {
						max = resource.Cost
					}
				}
			}
			return max
		}).
		AddAggregation("min_cost", func(data []interface{}) interface{} {
			min := 999999.0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					if resource.Cost < min {
						min = resource.Cost
					}
				}
			}
			return min
		}).
		AddAggregation("total_cpu", func(data []interface{}) interface{} {
			sum := 0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					sum += resource.CPUNum
				}
			}
			return sum
		}).
		AddAggregation("total_memory", func(data []interface{}) interface{} {
			sum := 0
			for _, item := range data {
				if resource, ok := item.(ResourceItem); ok {
					sum += resource.Memory
				}
			}
			return sum
		}).
		AddSortField("total_cost", false, nil)

	groupResult, err := result.Execute(testData)
	if err != nil {
		logger.Error("执行分组聚合失败: %v", err)
		return
	}

	logger.Info("复杂聚合结果: %+v", groupResult)
	for _, group := range groupResult.Groups {
		logger.Info("城市: %s, 数量: %d, 总成本: %.2f, 平均成本: %.2f, 最大成本: %.2f, 最小成本: %.2f, 总CPU: %d, 总内存: %d",
			group.Keys["city"],
			group.Aggregations["count"],
			group.Aggregations["total_cost"],
			group.Aggregations["avg_cost"],
			group.Aggregations["max_cost"],
			group.Aggregations["min_cost"],
			group.Aggregations["total_cpu"],
			group.Aggregations["total_memory"])
	}
}

// RunAllExamples 运行所有示例
func RunAllExamples() {
	logger.Info("开始运行多维度分组聚合示例...")

	ExampleMultiDimensionGroupBy()
	ExampleWithMapData()
	ExampleComplexAggregation()

	logger.Info("所有示例运行完成!")
}
