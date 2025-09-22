# 多维度 GROUP BY 聚合函数

这是一个通用的多维度分组聚合函数实现，支持灵活的数据分组、聚合计算、排序和过滤功能。

## 功能特性

- **多维度分组**: 支持按多个字段进行分组
- **灵活聚合**: 内置常用聚合函数，支持自定义聚合逻辑
- **排序支持**: 支持多字段排序，升序或降序
- **数据过滤**: 支持在聚合前进行数据过滤
- **类型安全**: 支持结构体和 Map 数据
- **高性能**: 优化的内存使用和计算效率

## 基本用法

### 1. 创建分组聚合器

```go
result := NewMultiDimensionGroupBy().
    AddGroupField("city", StringKeyExtractor("City")).
    AddGroupField("device_class", StringKeyExtractor("DeviceClass")).
    AddAggregation("count", Count).
    AddAggregation("total_cost", customCostSum).
    AddSortField("city", true, nil).
    AddSortField("count", false, nil)
```

### 2. 执行聚合

```go
groupResult, err := result.Execute(data)
if err != nil {
    log.Fatal(err)
}
```

### 3. 处理结果

```go
for _, group := range groupResult.Groups {
    fmt.Printf("城市: %s, 机型: %s, 数量: %d, 总成本: %.2f\n",
        group.Keys["city"], 
        group.Keys["device_class"],
        group.Aggregations["count"],
        group.Aggregations["total_cost"])
}
```

## 分组字段

### 内置键提取器

- `StringKeyExtractor(fieldName)`: 提取字符串字段
- `IntKeyExtractor(fieldName)`: 提取整数字段  
- `FloatKeyExtractor(fieldName)`: 提取浮点数字段
- `CustomKeyExtractor(func)`: 自定义提取逻辑

### 自定义键提取器示例

```go
// 按CPU范围分组
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
}))
```

## 聚合函数

### 内置聚合函数

- `Count`: 计数
- `Sum`: 求和
- `Avg`: 平均值
- `Max`: 最大值
- `Min`: 最小值
- `First`: 第一个值
- `Last`: 最后一个值

### 自定义聚合函数示例

```go
// 总成本聚合
AddAggregation("total_cost", func(data []interface{}) interface{} {
    sum := 0.0
    for _, item := range data {
        if resource, ok := item.(ResourceItem); ok {
            sum += resource.Cost
        }
    }
    return sum
})

// 平均成本聚合
AddAggregation("avg_cost", func(data []interface{}) interface{} {
    sum := 0.0
    for _, item := range data {
        if resource, ok := item.(ResourceItem); ok {
            sum += resource.Cost
        }
    }
    return sum / float64(len(data))
})
```

## 排序功能

```go
// 按城市升序，然后按数量降序
AddSortField("city", true, nil).      // 升序
AddSortField("count", false, nil)     // 降序
```

### 自定义排序键

```go
// 按成本范围排序
AddSortField("cost_range", true, func(value interface{}) interface{} {
    if cost, ok := value.(float64); ok {
        if cost < 100 {
            return "低"
        } else if cost < 500 {
            return "中"
        } else {
            return "高"
        }
    }
    return "未知"
})
```

## 数据过滤

```go
// 只统计活跃状态的资源
SetFilter(func(item interface{}) bool {
    if resource, ok := item.(ResourceItem); ok {
        return resource.Status == "active"
    }
    return false
})
```

## 完整示例

```go
package main

import (
    "fmt"
    "log"
)

type ResourceItem struct {
    ID          int     `json:"id"`
    City        string  `json:"city"`
    DeviceClass string  `json:"device_class"`
    CPUNum      int     `json:"cpu_num"`
    Memory      int     `json:"memory"`
    Cost        float64 `json:"cost"`
    Status      string  `json:"status"`
}

func main() {
    // 准备数据
    data := []interface{}{
        ResourceItem{ID: 1, City: "北京", DeviceClass: "C1", CPUNum: 4, Memory: 8, Cost: 100.0, Status: "active"},
        ResourceItem{ID: 2, City: "北京", DeviceClass: "C1", CPUNum: 4, Memory: 8, Cost: 100.0, Status: "active"},
        ResourceItem{ID: 3, City: "北京", DeviceClass: "C2", CPUNum: 8, Memory: 16, Cost: 200.0, Status: "active"},
        ResourceItem{ID: 4, City: "上海", DeviceClass: "C1", CPUNum: 4, Memory: 8, Cost: 120.0, Status: "active"},
        ResourceItem{ID: 5, City: "上海", DeviceClass: "C1", CPUNum: 4, Memory: 8, Cost: 120.0, Status: "inactive"},
    }

    // 创建分组聚合器
    result := NewMultiDimensionGroupBy().
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
        SetFilter(func(item interface{}) bool {
            if resource, ok := item.(ResourceItem); ok {
                return resource.Status == "active"
            }
            return false
        }).
        AddSortField("city", true, nil).
        AddSortField("count", false, nil)

    // 执行聚合
    groupResult, err := result.Execute(data)
    if err != nil {
        log.Fatal(err)
    }

    // 输出结果
    fmt.Printf("总分组数: %d\n", groupResult.Total)
    for _, group := range groupResult.Groups {
        fmt.Printf("城市: %s, 机型: %s, 数量: %d, 总成本: %.2f, 平均成本: %.2f\n",
            group.Keys["city"], 
            group.Keys["device_class"],
            group.Aggregations["count"],
            group.Aggregations["total_cost"],
            group.Aggregations["avg_cost"])
    }
}
```

## 性能考虑

- 对于大数据集，建议先进行数据过滤以减少处理量
- 避免在键提取器中进行复杂的计算
- 合理使用排序，避免不必要的排序操作
- 考虑使用并发处理来提升性能

## 扩展功能

### 支持 Map 数据

```go
mapData := []interface{}{
    map[string]interface{}{"city": "北京", "count": 10},
    map[string]interface{}{"city": "上海", "count": 5},
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
```

### 链式调用

所有配置方法都支持链式调用，使代码更加简洁：

```go
result := NewMultiDimensionGroupBy().
    AddGroupField("city", StringKeyExtractor("City")).
    AddGroupField("type", StringKeyExtractor("Type")).
    AddAggregation("count", Count).
    AddAggregation("sum", Sum).
    SetFilter(activeFilter).
    AddSortField("count", false, nil)
```

## 错误处理

函数会返回详细的错误信息：

- 没有指定分组字段
- 键提取器返回无效值
- 聚合函数执行失败
- 排序比较失败

建议在生产环境中添加适当的错误处理和日志记录。
