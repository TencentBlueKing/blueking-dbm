# 大 Key 批量提取工作流

## 场景
用户要求：给我拉一份某集群所有匹配特定后缀/模式的大 key 数据。

## 关键发现（2026-06-30 实战）

### 1. `redis_bigkey_log_query_bigkey_logs` 的局限

- **不传 ip**：返回全局 `by_instance` 字典，每个实例含 `top_keys`（按 sortBySize 和 sortByFields 的 TopN，通常每种排序各取 top 5-10）
- **传 ip**：返回 `{"bigkey_entries": [], "total_count": 0}` —— 如果该 IP 在查询时间范围内没有新的统计数据，可能为空
- **key_pattern 参数**：传了不生效，返回结果与不传完全一致

### 2. 正确方法：慢查询日志反向提取

```
工具: bkdbm-mcp-prod-redis-query-log.redis_query_log_query_slowlogs
```

**Step 1: 全局统计获取 proxy 列表**
```json
{
  "body_param": {
    "cluster_domain": "<domain>",
    "start_time": "<CST+08:00>",
    "end_time": "<CST+08:00>"
  }
}
```
返回 `by_instance` 的 keys 就是所有有慢查询的 proxy 地址列表。

**Step 2: 逐 proxy 拉详细日志**
```json
{
  "body_param": {
    "cluster_domain": "<domain>",
    "ip": "<ip>",
    "port": <port_int>,
    "start_time": "<CST+08:00>",
    "end_time": "<CST+08:00>"
  }
}
```
返回 `{"slowlog_entries": [...], "total_count": N}`，每条含完整 key 名。

**Step 3: 客户端侧过滤 + 去重**
- 按 `entry['key']` 匹配目标 suffix/pattern
- 按 key 聚合：count、max_duration_us、cmd、args sample

### 3. 性能参考

| 集群规模 | Proxy 数 | 耗时 |
|---------|---------|------|
| cache22.example.db (240 master) | 110 proxy | ~190 秒 |

### 4. 输出格式

用户通常期望 CSV 文件（可用 Excel 打开）：
```
序号,Key,命令,慢查询次数,最大耗时(ms)
1,9000000000000000001:1.36.11:wx:900000002:266437:3:ugc:hbgmi:ao,hmget,58254,4552.7
```

同时生成纯 key 列表 TXT 便于 grep/程序处理。

### 5. 注意事项

- 慢查询只记录超阈值的请求，如果目标 key 从未触发慢查询则提取不到
- 大 key 日志每天 08:00 在 slave 统计，只取 TopN，小于 TopN 阈值的不记录
- 两种方法覆盖的 key 集合不同：大 key 日志 = 体量大的 key；慢查询 = 耗时长的 key
- 对于 HMGET 大 Hash 场景，慢查询方法更有效（key 本身可能不大，但单次 HMGET 取 24 个 field 耗时长）
