# API 参数注意事项

## 目录

- 通用（`body_param` 包裹规则）
- `bkdbm-mcp-prod-redis-metrics` 接口 — 时间格式、合法 metric_type、group_by 限制
- `bkdbm-redis-query-log` 接口 — 慢日志查询参数
- `bkdbm-redis-query-alarm` 接口 — 告警查询参数
- `bkdbm-redis-query-meta` 接口 — 元数据与分页限制

---

## 通用

所有工具参数必须通过 `body_param` 包裹传入。

## bkdbm-mcp-prod-redis-metrics 接口

### 时间格式
必须 ISO 8601：`2026-04-17T08:00:00+08:00`，不能用 `2026-04-17 08:00:00`。

### 合法的 metric_type（master/slave/proxy）
```
cpu_usage, memory_usage, io_usage, disk_usage,
connections, qps, host_latency, command_latency, capacity
proxy 额外支持: latency_distribution（不支持 capacity）
```
**RocksDB 内部指标当前 MCP 接口不支持**（internal_key_skipped_count / delete_skipped_count / user_key_comparison_count 均返回\"不是合法选项\"）。
如果怀疑是 range scan 或 compaction 问题，可提醒用户自行在 DBM 平台或监控系统查这几个指标来验证：
- `internal_key_skipped_count` / `delete_skipped_count` → 验证 range scan 层级跳跃严重程度
- `user_key_comparison_count` → 验证 compaction 激烈程度
后续若平台支持，可直接通过 metrics 接口拉取。

### group_by 合法值
```
cluster_domain, ip, instance
command_latency 额外支持: （实测只能用 instance，bucket/cmd 不合法）
```

### cluster_proxy_series/stats 参数（⚠️ 两者都用 cluster_domains 数组）
```json
{
  "cluster_domains": ["ssd31.example.db"],   ← 复数，数组（proxy_series 和 proxy_stats 均如此）
  "metric_type": "host_latency",
  "group_by": ["cluster_domain"],
  "start_time": "2026-04-17T08:00:00+08:00",
  "end_time":   "2026-04-17T14:00:00+08:00",
  "max_len_datapoints": 15
}
```

**陷阱（2026-05-21 实测）**：`proxy_stats` 用 `cluster_domain`（单数）会返回 `{"cluster_domains": ["该字段是必填项。"]}` 报错。`master_stats` 同样需要 `cluster_domains` 数组，不是 `cluster_domain`。

### cluster_master_stats 参数
```json
{
  "cluster_domains": ["cache13.example.db"],   ← 复数，数组（同 proxy_stats）
  "metric_type": "host_latency",
  "group_by": ["ip"],
  "start_time": "...",
  "end_time": "..."
}
```

### redis_metrics_query_instance_series 参数
```json
{
  "instances": [{"ip": "192.168.2.11", "port": 30011}],  ← 对象数组，不是字符串
  "metric_type": "host_latency",
  "group_by": ["instance"],
  "start_time": "...",
  "end_time": "...",
  "max_len_datapoints": 15
}
```

### redis_metrics_query_machine_series 参数
```json
{
  "ips": ["192.168.2.11"],   ← 复数，数组
  "metric_type": "io_usage",
  "group_by": ["ip"],
  "start_time": "...",
  "end_time": "..."
}
```
注意：io_usage 在 machine 接口下实测返回 0，不可用于判断磁盘 IO 争抢。

### proxy_stats 大集群 JSON 截断处理（2026-06-09 实测）

集群 proxy 节点较多（如 46 个）时，`proxy_stats group_by=[ip]` 返回数据超过 65536 字节限制，JSON 会被截断。

**正确处理方式**：写入临时文件再用 `rfind("}")` 修复：
```python
r = subprocess.run(["mcporter", "call", "..."], capture_output=True, text=True, timeout=30)
with open("/tmp/proxy_lat.json", "w") as f:
    f.write(r.stdout)
with open("/tmp/proxy_lat.json") as f:
    content = f.read()
last = content.rfind("}")
content = content[:last+1]
resp = json.loads(content)
```
注意：若截断发生在 string value 中间，`rfind` 仍会 parse error，此时需进一步缩减数据量（减少 max_len_datapoints 或分批查询）。

## bkdbm-redis-query-log 接口

### ⚠️ 工具名勘误（2026-05-21 实测）

**旧名已废弃**：`redis_query_log_get_cluster_slowlog_statics` → 调用报 `unknown tool`。

**正确工具名（3 个工具）**：

| 工具名 | 用途 |
|--------|------|
| `redis_query_log_query_slowlogs` | 慢查询统计/列表（**替代旧工具**） |
| `redis_bigkey_log_query_bigkey_logs` | 大 key 日志（非实时，每日 8 点统计） |
| `redis_server_log_query_server_logs` | server log（Twemproxy / Redis 服务端日志） |

### redis_query_log_query_slowlogs 参数
```json
{
  "cluster_domain": "cache27.example.db",
  "start_time": "2026-05-21T11:23:00",
  "end_time":   "2026-05-21T11:30:00"
}
```
返回结构：`data.by_instance`（key 为 `ip:port`）+ `data.summary`。

**慢日志返回字段（by_instance 每个实例）：**
```json
{
  "duration_stats": {"avg_ms": 174.09, "max_ms": 221.73, "median_ms": 178.38, "min_ms": 101.84},
  "slowest_query": {"cmd": "hGet", "create_time": "...", "duration_ms": 221.73, "key": "grpa:yxzj:..."},
  "top_commands": {"hGet": 4, "get": 3},
  "total_count": 7
}
```

### redis_server_log_query_server_logs 参数
```json
{
  "cluster_domain": "ssd31.example.db",
  "ip": "192.168.2.11",
  "port": 30011,
  "start_time": "...",
  "end_time": "..."
}
```
TendisSSD server log 内容为 RocksDB `Level subcompaction finished` 日志，属正常现象。

## bkdbm-redis-query-alarm 接口

```json
{
  "cluster_domain": "ssd31.example.db",
  "start_time": "2026-04-17T08:00:00+08:00",
  "end_time":   "2026-04-17T14:00:00+08:00"
}
```

## bkdbm-redis-query-meta 接口

### redis_query_meta_cluster_basic_overview 参数名陷阱（2026-05-21 实测）

```json
{
  "cluster_domain": "ssd49.example.db"   ← 必须用 cluster_domain，不是 immute_domain
}
```

错误示范（会报 `cluster_id or cluster_domain is required`）：
```json
{ "immute_domain": "ssd49.example.db" }   ← ❌ 报错
```

### redis_query_meta_list_cluster_proxies — 查 proxy 地区归属（2026-06-09 新增）

server：`bkdbm-mcp-prod-redis-query-meta`

```json
{
  "cluster_domain": "tendisplus-3.example.db",
  "page_size": 100,
  "page": 1
}
```

返回字段：
```json
{
  "page": 1,
  "page_size": 80,
  "proxies": [
    {
      "address": "192.168.2.14:50010",
      "cls_name": "SA2.LARGE8",
      "status": "running",
      "sub_zone": "上海-松江",          ← 机房地区，用于按地区分组分析
      "version": "predixy-1.6.1"
    }
  ]
}
```

**用途**：当用户怀疑某个机房/地区有网络问题时，用此接口获取各 proxy 的 `sub_zone`，与延迟数据 join 后按地区分组分析。如所有地区均高延迟，可排除网络区域因素。

**实测地区值示例**：上海-富特、上海-宝信、上海-松江、上海-青浦、上海-花桥

### dbmeta_query_list_machine_info — 查 master 机器地区归属（2026-06-09 新增）

server：`bkdbm-mcp-prod-dbmeta-query`

```json
{ "ips": ["192.168.2.15", "192.168.2.16"] }
```

**注意：每批 ≤ 15 个 IP，超过会超时。**

返回结构：`data.machines[]`，关键字段：

```json
{
  "ip": "192.168.2.15",
  "bk_sub_zone": "上海-花桥",
  "bk_idc_name": "昆山腾讯万国DC",
  "bk_idc_area": "华东",
  "bk_cloud_id": 0
}
```

**用途**：proxy 接口直接有 `sub_zone`，但 master 没有，需用此接口补充地区信息后 join 延迟数据做地区分布分析。

**实测地区分布（tendisplus-3.example.db，2026-06-09）**：

| 地区 | 机房 | master 数 | avg延迟 |
|------|------|:---------:|:-------:|
| 上海-青浦 | 上海电信青浦DC | 7 | 116.5ms |
| 上海-宝信 | 上海腾讯宝信DC | 6 | 114.5ms |
| 上海-松江 | 上海腾讯松江DC | 2 | 113.1ms |
| 上海-花桥 | 昆山腾讯万国DC | 15 | 110.3ms |

各地区仅差 6ms → 排除地区性网络因素，后确认为整体网络问题。

### redis_metrics stats 响应字段（2026-05-21 实测）

metrics stats 类工具响应中统计字段是 **`p95`** 不是 `p99`：
```
avg, cv, latest, max, median, min, p95, trend, trend_unit
```
❌ `p99` 不存在，解析时不要用 `node['p99']`，改用 `node['p95']`。

### list_tools 输出超长截断陷阱（2026-05-21）

`metrics` server 的 `list_tools` 输出约 20000 字节，在 `execute_code` 里 `json.loads` 会因截断报 JSONDecodeError。
**正确做法：用 terminal pipe 解析**：

```bash
python3 mcp_client.py --user operator --server bkdbm-mcp-prod-redis-metrics --action list_tools \
  | python3 -c "import json,sys; tools=json.load(sys.stdin)['tools']; [print(t['name']) for t in tools]"
```
