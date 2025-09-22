/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package statistic

import (
	"strings"
	"testing"
)

// contains 检查字符串是否包含子字符串
func contains(s, substr string) bool {
	return strings.Contains(s, substr)
}

// TestResourceItem 测试用的数据结构
type TestResourceItem struct {
	ID          int     `json:"id"`
	City        string  `json:"city"`
	DeviceClass string  `json:"device_class"`
	CPUNum      int     `json:"cpu_num"`
	Memory      int     `json:"memory"`
	Cost        float64 `json:"cost"`
	Status      string  `json:"status"`
}

// TestMultiDimensionGroupBy 测试多维度分组聚合
func TestMultiDimensionGroupBy(t *testing.T) {
	// 准备测试数据
	testData := []interface{}{
		TestResourceItem{ID: 1, City: "北京", DeviceClass: "C1", CPUNum: 4, Memory: 8, Cost: 100.0, Status: "active"},
		TestResourceItem{ID: 2, City: "北京", DeviceClass: "C1", CPUNum: 4, Memory: 8, Cost: 100.0, Status: "active"},
		TestResourceItem{ID: 3, City: "北京", DeviceClass: "C2", CPUNum: 8, Memory: 16, Cost: 200.0, Status: "active"},
		TestResourceItem{ID: 4, City: "上海", DeviceClass: "C1", CPUNum: 4, Memory: 8, Cost: 120.0, Status: "active"},
		TestResourceItem{ID: 5, City: "上海", DeviceClass: "C1", CPUNum: 4, Memory: 8, Cost: 120.0, Status: "inactive"},
	}

	// 测试基本分组功能
	t.Run("基本分组功能", func(t *testing.T) {
		result := NewMultiDimensionGroupBy().
			AddGroupField("city", StringKeyExtractor("City")).
			AddGroupField("device_class", StringKeyExtractor("DeviceClass")).
			AddAggregation("count", Count)

		groupResult, err := result.Execute(testData)
		if err != nil {
			t.Fatalf("执行分组聚合失败: %v", err)
		}
		if groupResult == nil {
			t.Fatal("分组结果为空")
		}
		if groupResult.Total != 3 {
			t.Fatalf("期望3个分组，实际得到%d个", groupResult.Total)
		}

		// 验证分组结果
		expectedGroups := map[string]int{
			"北京|C1": 2,
			"北京|C2": 1,
			"上海|C1": 2,
		}

		for _, group := range groupResult.Groups {
			key := group.Keys["city"].(string) + "|" + group.Keys["device_class"].(string)
			expectedCount, exists := expectedGroups[key]
			if !exists {
				t.Fatalf("未找到预期的分组: %s", key)
			}
			if group.Aggregations["count"] != expectedCount {
				t.Fatalf("分组 %s 的数量不正确，期望%d，实际%d", key, expectedCount, group.Aggregations["count"])
			}
		}
	})

	// 测试聚合函数
	t.Run("聚合函数测试", func(t *testing.T) {
		result := NewMultiDimensionGroupBy().
			AddGroupField("city", StringKeyExtractor("City")).
			AddAggregation("count", Count).
			AddAggregation("total_cost", func(data []interface{}) interface{} {
				sum := 0.0
				for _, item := range data {
					if resource, ok := item.(TestResourceItem); ok {
						sum += resource.Cost
					}
				}
				return sum
			}).
			AddAggregation("avg_cost", func(data []interface{}) interface{} {
				sum := 0.0
				for _, item := range data {
					if resource, ok := item.(TestResourceItem); ok {
						sum += resource.Cost
					}
				}
				return sum / float64(len(data))
			})

		groupResult, err := result.Execute(testData)
		if err != nil {
			t.Fatalf("执行分组聚合失败: %v", err)
		}

		// 验证北京的分组结果
		var beijingGroup *GroupResult
		for _, group := range groupResult.Groups {
			if group.Keys["city"] == "北京" {
				beijingGroup = &group
				break
			}
		}
		if beijingGroup == nil {
			t.Fatal("未找到北京分组")
		}
		if beijingGroup.Aggregations["count"] != 3 {
			t.Fatalf("北京分组数量不正确，期望3，实际%d", beijingGroup.Aggregations["count"])
		}
		if beijingGroup.Aggregations["total_cost"] != 400.0 {
			t.Fatalf("北京分组总成本不正确，期望400.0，实际%v", beijingGroup.Aggregations["total_cost"])
		}
		expectedAvg := 400.0 / 3.0
		if beijingGroup.Aggregations["avg_cost"] != expectedAvg {
			t.Fatalf("北京分组平均成本不正确，期望%v，实际%v", expectedAvg, beijingGroup.Aggregations["avg_cost"])
		}
	})

	// 测试过滤功能
	t.Run("过滤功能测试", func(t *testing.T) {
		result := NewMultiDimensionGroupBy().
			AddGroupField("city", StringKeyExtractor("City")).
			AddAggregation("active_count", Count).
			SetFilter(func(item interface{}) bool {
				if resource, ok := item.(TestResourceItem); ok {
					return resource.Status == "active"
				}
				return false
			})

		groupResult, err := result.Execute(testData)
		if err != nil {
			t.Fatalf("执行分组聚合失败: %v", err)
		}

		// 验证只有活跃资源被统计
		var shanghaiGroup *GroupResult
		for _, group := range groupResult.Groups {
			if group.Keys["city"] == "上海" {
				shanghaiGroup = &group
				break
			}
		}
		if shanghaiGroup == nil {
			t.Fatal("未找到上海分组")
		}
		if shanghaiGroup.Aggregations["active_count"] != 1 {
			t.Fatalf("上海分组活跃数量不正确，期望1，实际%d", shanghaiGroup.Aggregations["active_count"])
		} // 上海只有1个活跃资源
	})

	// 测试排序功能
	t.Run("排序功能测试", func(t *testing.T) {
		result := NewMultiDimensionGroupBy().
			AddGroupField("city", StringKeyExtractor("City")).
			AddAggregation("count", Count).
			AddSortField("count", false, nil) // 按数量降序

		groupResult, err := result.Execute(testData)
		if err != nil {
			t.Fatalf("执行分组聚合失败: %v", err)
		}

		// 验证排序结果
		if len(groupResult.Groups) < 2 {
			t.Fatal("分组数量不足，无法验证排序")
		}
		firstCount := groupResult.Groups[0].Aggregations["count"].(int)
		secondCount := groupResult.Groups[1].Aggregations["count"].(int)
		if firstCount < secondCount {
			t.Fatal("排序结果不正确")
		}
	})

	// 测试自定义键提取器
	t.Run("自定义键提取器测试", func(t *testing.T) {
		result := NewMultiDimensionGroupBy().
			AddGroupField("cpu_range", CustomKeyExtractor(func(item interface{}) string {
				if resource, ok := item.(TestResourceItem); ok {
					if resource.CPUNum <= 4 {
						return "低配置"
					} else {
						return "高配置"
					}
				}
				return "未知"
			})).
			AddAggregation("count", Count)

		groupResult, err := result.Execute(testData)
		if err != nil {
			t.Fatalf("执行分组聚合失败: %v", err)
		}

		// 验证自定义分组
		var lowConfigGroup *GroupResult
		var highConfigGroup *GroupResult
		for _, group := range groupResult.Groups {
			if group.Keys["cpu_range"] == "低配置" {
				lowConfigGroup = &group
			} else if group.Keys["cpu_range"] == "高配置" {
				highConfigGroup = &group
			}
		}
		if lowConfigGroup == nil {
			t.Fatal("未找到低配置分组")
		}
		if highConfigGroup == nil {
			t.Fatal("未找到高配置分组")
		}
		if lowConfigGroup.Aggregations["count"] != 4 {
			t.Fatalf("低配置分组数量不正确，期望4，实际%d", lowConfigGroup.Aggregations["count"])
		} // 4个低配置资源
		if highConfigGroup.Aggregations["count"] != 1 {
			t.Fatalf("高配置分组数量不正确，期望1，实际%d", highConfigGroup.Aggregations["count"])
		} // 1个高配置资源
	})
}

// TestPredefinedAggregationFunctions 测试预定义的聚合函数
func TestPredefinedAggregationFunctions(t *testing.T) {
	testData := []interface{}{1, 2, 3, 4, 5}

	t.Run("Count聚合函数", func(t *testing.T) {
		result := Count(testData)
		if result != 5 {
			t.Fatalf("Count结果不正确，期望5，实际%d", result)
		}
	})

	t.Run("Sum聚合函数", func(t *testing.T) {
		result := Sum(testData)
		if result != 15 {
			t.Fatalf("Sum结果不正确，期望15，实际%d", result)
		}
	})

	t.Run("Avg聚合函数", func(t *testing.T) {
		result := Avg(testData)
		if result != 3.0 {
			t.Fatalf("Avg结果不正确，期望3.0，实际%v", result)
		}
	})

	t.Run("Max聚合函数", func(t *testing.T) {
		result := Max(testData)
		if result != 5 {
			t.Fatalf("Max结果不正确，期望5，实际%d", result)
		}
	})

	t.Run("Min聚合函数", func(t *testing.T) {
		result := Min(testData)
		if result != 1 {
			t.Fatalf("Min结果不正确，期望1，实际%d", result)
		}
	})

	t.Run("First聚合函数", func(t *testing.T) {
		result := First(testData)
		if result != 1 {
			t.Fatalf("First结果不正确，期望1，实际%d", result)
		}
	})

	t.Run("Last聚合函数", func(t *testing.T) {
		result := Last(testData)
		if result != 5 {
			t.Fatalf("Last结果不正确，期望5，实际%d", result)
		}
	})
}

// TestKeyExtractors 测试键提取器
func TestKeyExtractors(t *testing.T) {
	testItem := TestResourceItem{
		ID:          1,
		City:        "北京",
		DeviceClass: "C1",
		CPUNum:      4,
		Memory:      8,
		Cost:        100.5,
	}

	t.Run("StringKeyExtractor", func(t *testing.T) {
		extractor := StringKeyExtractor("City")
		result := extractor(testItem)
		if result != "北京" {
			t.Fatalf("StringKeyExtractor结果不正确，期望北京，实际%s", result)
		}
	})

	t.Run("IntKeyExtractor", func(t *testing.T) {
		extractor := IntKeyExtractor("CPUNum")
		result := extractor(testItem)
		if result != "4" {
			t.Fatalf("IntKeyExtractor结果不正确，期望4，实际%s", result)
		}
	})

	t.Run("FloatKeyExtractor", func(t *testing.T) {
		extractor := FloatKeyExtractor("Cost")
		result := extractor(testItem)
		if result != "100.50" {
			t.Fatalf("FloatKeyExtractor结果不正确，期望100.50，实际%s", result)
		}
	})

	t.Run("CustomKeyExtractor", func(t *testing.T) {
		extractor := CustomKeyExtractor(func(item interface{}) string {
			if resource, ok := item.(TestResourceItem); ok {
				return resource.City + "_" + resource.DeviceClass
			}
			return ""
		})
		result := extractor(testItem)
		if result != "北京_C1" {
			t.Fatalf("CustomKeyExtractor结果不正确，期望北京_C1，实际%s", result)
		}
	})
}

// TestErrorHandling 测试错误处理
func TestErrorHandling(t *testing.T) {
	t.Run("没有分组字段", func(t *testing.T) {
		result := NewMultiDimensionGroupBy()
		_, err := result.Execute([]interface{}{1, 2, 3})
		if err == nil {
			t.Fatal("期望返回错误，但实际没有错误")
		}
		if !contains(err.Error(), "至少需要指定一个分组字段") {
			t.Fatalf("错误信息不正确，期望包含'至少需要指定一个分组字段'，实际: %s", err.Error())
		}
	})

	t.Run("空数据", func(t *testing.T) {
		result := NewMultiDimensionGroupBy().
			AddGroupField("test", StringKeyExtractor("Test"))
		groupResult, err := result.Execute([]interface{}{})
		if err != nil {
			t.Fatalf("执行空数据分组聚合失败: %v", err)
		}
		if groupResult.Total != 0 {
			t.Fatalf("空数据分组结果总数不正确，期望0，实际%d", groupResult.Total)
		}
		if len(groupResult.Groups) != 0 {
			t.Fatalf("空数据分组结果组数不正确，期望0，实际%d", len(groupResult.Groups))
		}
	})
}

// TestMapData 测试Map数据
func TestMapData(t *testing.T) {
	mapData := []interface{}{
		map[string]interface{}{"city": "北京", "count": 10},
		map[string]interface{}{"city": "北京", "count": 5},
		map[string]interface{}{"city": "上海", "count": 8},
	}

	result := NewMultiDimensionGroupBy().
		AddGroupField("city", func(item interface{}) string {
			if m, ok := item.(map[string]interface{}); ok {
				if city, exists := m["city"]; exists {
					return city.(string)
				}
			}
			return ""
		}).
		AddAggregation("total_count", func(data []interface{}) interface{} {
			sum := 0
			for _, item := range data {
				if m, ok := item.(map[string]interface{}); ok {
					if count, exists := m["count"]; exists {
						sum += count.(int)
					}
				}
			}
			return sum
		})

	groupResult, err := result.Execute(mapData)
	if err != nil {
		t.Fatalf("执行Map数据分组聚合失败: %v", err)
	}
	if groupResult.Total != 2 {
		t.Fatalf("Map数据分组结果总数不正确，期望2，实际%d", groupResult.Total) // 北京和上海两个分组
	}

	// 验证北京分组
	var beijingGroup *GroupResult
	for _, group := range groupResult.Groups {
		if group.Keys["city"] == "北京" {
			beijingGroup = &group
			break
		}
	}
	if beijingGroup == nil {
		t.Fatal("未找到北京分组")
	}
	if beijingGroup.Aggregations["total_count"] != 15 {
		t.Fatalf("北京分组总数量不正确，期望15，实际%d", beijingGroup.Aggregations["total_count"]) // 10+5
	}
}

// BenchmarkMultiDimensionGroupBy 性能测试
func BenchmarkMultiDimensionGroupBy(b *testing.B) {
	// 准备大量测试数据
	testData := make([]interface{}, 10000)
	for i := 0; i < 10000; i++ {
		testData[i] = TestResourceItem{
			ID:          i,
			City:        []string{"北京", "上海", "深圳", "广州"}[i%4],
			DeviceClass: []string{"C1", "C2", "C3"}[i%3],
			CPUNum:      []int{4, 8, 16}[i%3],
			Memory:      []int{8, 16, 32}[i%3],
			Cost:        float64(100 + i%500),
			Status:      []string{"active", "inactive"}[i%2],
		}
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		result := NewMultiDimensionGroupBy().
			AddGroupField("city", StringKeyExtractor("City")).
			AddGroupField("device_class", StringKeyExtractor("DeviceClass")).
			AddAggregation("count", Count).
			AddAggregation("total_cost", func(data []interface{}) interface{} {
				sum := 0.0
				for _, item := range data {
					if resource, ok := item.(TestResourceItem); ok {
						sum += resource.Cost
					}
				}
				return sum
			})

		_, err := result.Execute(testData)
		if err != nil {
			b.Fatal(err)
		}
	}
}
