# saveproxyconnlog - ConnLog 解析性能优化

## 日志格式

```
2026-06-29 23:55:07: (critical) conn_log, current user is 'user1'@'1.2.3.4' 147550633
```

字段：`conn_time`, `user`, `client_host`, `thread_id`

## 解析函数版本

### V1 - 正则版本 (`parseConnLogLine`)

使用 `regexp.FindStringSubmatch` + `time.ParseInLocation` + `strconv.ParseInt`。

### V2 - 字符串切片 + 手动时间解析 (`parseConnLogLineV2`)

核心优化点：

1. **锚点快速过滤**：`strings.Index(line, "conn_log, current user is '")` 一次判断跳过非目标行
2. **固定偏移提取字段**：利用日志格式固定的特点，通过 `strings.Index` + 切片定位 user、host、thread_id
3. **手动时间解析 `parseTimeFast`**：时间格式完全固定（`YYYY-MM-DD HH:MM:SS`），直接按字节偏移提取年月日时分秒，避免 `time.ParseInLocation` 的格式字符串解析开销
4. **unsafe 零拷贝**：`unsafe.Slice(unsafe.StringData(line), 19)` 将 string 前 19 字节零拷贝转为 `[]byte` 传入 `parseTimeFast`

## Benchmark 结果

测试环境：Apple M4 Pro, Go 1.22+, `go test -bench -benchmem -count=3`

### 匹配行（conn_log 行）

| 版本 | ns/op | B/op | allocs/op |
|------|-------|------|-----------|
| V1 (正则) | 3,340 | 900 | 12 |
| **V2 (优化)** | **260** | **256** | **4** |

**V2 比 V1 快 12.8 倍，内存分配减少 71%**

### 不匹配行（非 conn_log 行）

| 版本 | ns/op | B/op | allocs/op |
|------|-------|------|-----------|
| V1 (正则) | 16 | 0 | 0 |
| V2 (优化) | 26 | 0 | 0 |

不匹配行两者都极快（纳秒级），差异可忽略。

### 混合场景（80% 不匹配 + 20% 匹配，最接近生产）

| 版本 | ns/op | B/op | allocs/op |
|------|-------|------|-----------|
| V1 (正则) | 3,460 | 900 | 12 |
| **V2 (优化)** | **363** | **256** | **4** |

**V2 比 V1 快 9.5 倍**

## 性能瓶颈分析

V1 的主要开销来源：

| 开销来源 | 占比 | V2 优化手段 |
|----------|------|-------------|
| `regexp.FindStringSubmatch` | ~40% | `strings.Index` + 切片定位 |
| `time.ParseInLocation` | ~45% | `parseTimeFast` 手动字节解析 |
| `strconv.ParseInt` | ~5% | 保留（开销已很小） |
| submatch 切片分配 | ~10% | 无额外切片分配 |

## 运行 Benchmark

```bash
cd dbm-services/mysql/db-tools/mysql-monitor
go test -bench=BenchmarkParse -benchmem -count=3 ./pkg/itemscollect/saveproxyconnlog/
```
