---
name: dbm-redis-hotkey-diagnose
description: Redis 热点 key 问题排查 skill。当出现以下情况时触发：某实例 QPS 远超其他实例、单核 CPU 打满/告警、proxy 慢查询集中在同一个 key、访问耗时飙升但内存正常、ZRANGE/HGETALL/SMEMBERS 等命令耗时高。适用于 DBM 蓝鲸平台 TwemproxyRedis / PredixyTendisplusCluster 集群。
metadata: {"version":"1.0.3","space_id":"1d3d86fa67bef8c3","bk_skill_code":"dbm-redis-hotkey-diagnose","openclaw":{"category":"tencent","emoji":"","requires":{"env":[]}}}
---

# Redis 热点 Key 排查

## 典型现象
- 单实例 QPS 占集群 **> 50%**，其他实例流量极低
- 主机单核 CPU **100%** 告警
- 集群平均访问耗时告警（proxy 侧 > 1000ms）
- 慢查询全部指向同一个 key，命令为 `ZRANGE`/`HGETALL`/`SMEMBERS`/`ZRANK` 等
- master 实例无 slowlog（CPU 调度瓶颈，命令本身执行快）

---

## 时间格式规范

⚠️ **所有时间参数统一使用 CST 带时区格式，不要手动转 UTC**

```
正确：2026-03-27T09:18:00+08:00
错误：2026-03-27T01:18:00Z   ← 禁止手动 -8h
```

告警时间前后各扩 ±30 分钟作为查询范围。

---

## MCP 工具调用规范

⚠️ **所有 MCP 工具调用使用 mcporter CLI，参数必须包在 `body_param` 外层**

```bash
mcporter call bkdbm-mcp-prod-redis-<server>.<tool> \
  --args '{"body_param": {<参数>}}' \
  --config "$TEMP_CONFIG"
```

---

## 排查流程

### Step 1：定位热点实例（先拉全量实例 QPS，取 TOP N 与集群平均对比）

**1.1 拉取集群后端 master 实例列表**

```bash
mcporter call bkdbm-mcp-prod-redis-query-meta.redis_query_meta_list_cluster_masters \
  --args '{"body_param": {"cluster_domain": "<domain>"}}' \
  --config "$TEMP_CONFIG"
```

**1.2 拉取各实例 QPS，找 QPS TOP N，并对比集群平均 QPS/CPU**

把实例列表交给拆分脚本（两种传法任选：`ip:port` 逗号分隔；或把 1.1 的返回 JSON 存盘后传文件路径，脚本自动提取）。脚本并发拉取每个实例的 QPS 与 CPU，输出全实例明细、集群基准（平均 QPS / 平均 CPU）和 TOP N 对比表：

```bash
python3 "$SKILL_DIR/scripts/instance_qps_split.py" \
  <domain> <ip:port,ip:port,... | masters.json> <start_cst+08:00> <end_cst+08:00> [top_n=5]
```

其中 `$SKILL_DIR` 为本 SKILL.md 所在目录。若不确定，先用 `find ~ -name instance_qps_split.py -path '*redis-hotkey-diagnose*' 2>/dev/null` 定位。

**1.3 对比与判定**（脚本已自动计算倍数，按输出结论执行）

| 信号 | 标准 |
|------|------|
| TOP 实例 QPS vs 集群平均 QPS | ≥ 3x → 候选热点实例 |
| 单实例 QPS 占比 | ≥ 50% → 候选热点实例 |
| 该实例 CPU vs 集群平均 CPU | ≥ 3x 或接近单核 100% → 交叉确认热点 |

满足任一 QPS 信号即记录 `ip:port` 进入 Step 2。CPU 信号用于交叉确认：QPS 高但 CPU 低 = 流量大但命令轻，仍需 Step 2 慢日志佐证是否热点 key。

⚠️ CPU 为主机级指标，同 IP 多实例共享，集群平均 CPU 按 IP 去重计算；QPS 为实例级（端口级）。

---

### Step 2：确认热点 Key

> ⚠️ **工具名勘误**：`redis_query_log_get_cluster_slowlog_statics` 已废弃，正确工具名为 `redis_query_log_query_slowlogs`。

```bash
mcporter call bkdbm-mcp-prod-redis-query-log.redis_query_log_query_slowlogs \
  --args '{"body_param": {"cluster_domain": "<domain>", "start_time": "<CST+08:00>", "end_time": "<CST+08:00>"}}' \
  --config "$TEMP_CONFIG"
```

关注 `by_instance` 中各 proxy 的 `slowest_query.key`：
- **各 proxy 指向同一个 key** → 确认热点 key
- 记录：`key` 名称、命令类型、最大耗时

---

### Step 3：评估 Key 规模

连接到热点实例，执行对应命令：

| key 类型 | 评估命令 | 危险阈值 |
|---------|---------|---------|
| sorted set | `ZCARD <key>` | > 10万 member |
| hash | `HLEN <key>` | > 10万 field |
| set | `SCARD <key>` | > 10万 member |
| list | `LLEN <key>` | > 10万 element |
| string | `STRLEN <key>` | > 1MB |

---

### Step 4：交叉验证告警

```bash
mcporter call bkdbm-mcp-prod-redis-query-alarm.redis_query_alarm_fetch_app_alarms \
  --args '{"body_param": {"bk_biz_id": <id>, "start_time": "<CST+08:00>", "end_time": "<CST+08:00>"}}' \
  --config "$TEMP_CONFIG"
```

预期告警：
- `Redis(TendisCache)主机单核CPU使用率` — target_key 指向热点实例所在机器
- `Redis(TendisCache)集群平均访问耗时` — description 含高耗时值（ms）

---

### Step 5：输出根因链路

根因链路格式：
```
热点 key: <key_name>（类型: sorted_set，成员数: N）
  → ZRANGE 请求全部 hash 到 <ip>:<port>（占集群 QPS xx%）
  → <ip> 单核 CPU 100%（告警触发于 HH:MM）
  → proxy 等待耗时飙升（均值 xxms，最大 xxms）
  → 客户端超时/降级 → 集群 QPS 从峰值下降
```

---

### Step 6：处置建议

**立即**
- 确认业务方是否有异常流量（发版/活动/爬虫）
- 对该 key 的访问增加本地缓存（JVM/进程级），减少直接打 Redis

**短期**
- 对大 sorted set 按 hash 前缀拆分为多个子 key（如 `key:0`~`key:N`）
- 业务侧增加访问频率限制

**长期**
- 评估是否需要扩容该 master 实例
- 排查 Twemproxy 分片策略，确认 hash 规则是否导致数据倾斜

---

## 参数注意事项

| 工具 | 字段注意 |
|------|---------|
| `redis_metrics_query_cluster_proxy_series` | 必填 `cluster_domains`（数组）+ `group_by`（数组） |
| `redis_query_log_query_slowlogs` | 慢查询在 proxy（端口52602），master 无记录 |
| 时间格式 | CST 带时区：`2026-03-27T09:18:00+08:00`，禁止手动转 UTC |
| 所有 redis-metrics/query-meta/query-log 参数 | 必须包在 `body_param` 外层 |

## 参考
- 实例 QPS 拆分脚本：`scripts/instance_qps_split.py`
- 热点 key 处置方案：`references/hotkey_solutions.md`
- 大 Key 批量提取工作流：`references/bigkey-batch-extract.md`

## 按 Key 后缀/模式批量提取大 Key 列表

当用户要求"拉取某个后缀/模式的所有大 key"时，走以下流程：

### 方案 A：大 Key 日志（redis_bigkey_log_query_bigkey_logs）

- **全局模式**（不传 ip）：返回 `by_instance` → 每个实例的 `top_keys`（按 size/fields 的 TopN）
- **实例模式**（传 ip + port）：返回 `bigkey_entries` 详细列表
- ⚠️ **限制**：大 key 日志每天早上 8 点在 slave 统计一次（非实时），且只取 TopN。如果目标 key 体量不够进入 TopN，则**查不到**
- ⚠️ **key_pattern 参数不生效**：传了也返回全局 TopN，不做服务端过滤

### 方案 B：慢查询日志提取（推荐，实时性好）

当大 key 日志查不到时，通过 **slowlog 反向提取**所有匹配 key：

1. **全局慢查询统计**（不传 ip）→ 获取 `by_instance` 中所有 proxy 列表
2. **逐 proxy 拉取详细慢查询**（传 ip + port）→ 返回 `slowlog_entries`（最多 1000 条/实例）
3. **客户端侧过滤** `entry['key']` 匹配目标后缀
4. **去重汇总**：按 key 聚合 count、max_duration_us
5. **输出 CSV 文件**：序号、Key、命令、慢查询次数、最大耗时

```python
# slowlog entry 结构：
{
    "args": ["field1", "field2", ...],  # HMGET 的 fields 列表
    "cmd": "hmget",
    "create_time": "2026-06-30T04:00:01.460162261+08:00",
    "duration": {"us": 1324863},
    "duration_us": 1324863,
    "id": 134777651,
    "instance_addr": "192.168.2.1:50022",
    "instance_role": "proxy",
    "key": "900000000001:1.36.11:wx:c:266437:3:a:b:ao"
}
```

**注意事项：**
- 大集群可能有 100+ proxy，逐个查询耗时约 2-3 分钟
- slowlog 只记录超过阈值的慢查询，非慢查询的 key 不会出现
- 输出文件格式：CSV（方便用户导入 Excel）+ 纯 key 列表 TXT

### 工具对照

| 需求 | 工具 | 服务器 |
|------|------|--------|
| 大 key TopN 统计 | `redis_bigkey_log_query_bigkey_logs` | `bkdbm-mcp-prod-redis-query-log` |
| 慢查询按 key 提取 | `redis_query_log_query_slowlogs` | `bkdbm-mcp-prod-redis-query-log` |
| 集群 bigkey 报告记录 | `redis_reports_query_reports_by_cluster` | `bkdbm-mcp-prod-redis-reports` |

---

## Pitfalls

1. **热点 key 可能无慢日志**
   热点 key 命令执行快（微秒级），不触发慢日志阈值，master 无 slowlog 不代表无热点，需结合 QPS 分布判断。

2. **单实例 QPS 高 ≠ 热点 key**
   需排除：该实例是否承载了更多 slot（数据分布不均）、是否有定时任务打到该实例。QPS 集中 + 慢查询指向同一 key 才能确认热点。

3. **group_by ["instance"] 不支持**
   master_series 的 group_by 只支持 ["ip"] 或 ["cluster_domain"]，实例级 QPS 需用 group_by ["ip"] 后按端口匹配。

4. **热点 key 处置前必须确认 key 归属业务**
   不能直接删 key 或建议扩容，需先确认 key 对应哪个业务模块，再给针对性建议（本地缓存/读写分离/拆分 key）。

5. **HGETALL/SMEMBERS 慢不等于热点 key**
   HGETALL 慢可能是大 Hash，SMEMBERS 慢可能是大 Set，这是「大 key」问题，根因和处置与热点 key 不同，注意区分。

6. **大 key 日志 API 的 key_pattern 参数不生效**
   `redis_bigkey_log_query_bigkey_logs` 传 `key_pattern` 不做服务端过滤，返回仍是全局 TopN。要按模式搜索 key 必须走慢查询日志逐 proxy 提取。

7. **大 key 日志传 ip 可能返回空**
   传 ip 时返回 `bigkey_entries: []` 不代表该实例无大 key，可能是时间范围不匹配（统计每天 08:00 一次）。用不传 ip 的全局模式能看到 top_keys。

8. **HMGET 多 field 造成的"大 key"不在大 key 日志中**
   HMGET 取 20+ fields 导致单次返回数据大、耗时长，但 Hash 本身 field 数/size 可能不够进入 TopN。这类 key 只能通过慢查询日志发现。

9. **`redis_query_log_get_cluster_slowlog_statics` 已废弃**
   该工具名已从 DBM MCP 移除，正确工具名为 `redis_query_log_query_slowlogs`（server: `bkdbm-mcp-prod-redis-query-log`）。

10. **所有 MCP 参数必须包在 `body_param` 外层**
    mcporter call 时，参数必须嵌套在 `body_param` 键下，否则报 `cluster_id or cluster_domain is required`。
