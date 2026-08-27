---
name: redis-latency-diagnose
description: Redis 集群延迟问题诊断 skill。当用户反馈 Redis 集群延迟高、访问慢、超时告警时触发。按照标准六步流程逐层排查：集群整体延迟趋势 → 命令级分析 → proxy 层是否全局/局部问题 → 后端 master 节点定位 → 节点 QPS/延迟/CPU 综合分析 → 结合慢日志验证。适用于 DBM 蓝鲸平台管理的所有 Redis 集群类型（TwemproxyRedisInstance、TwemproxyTendisSSDInstance、PredixyTendisplusCluster 等）。
metadata: {"version":"1.0.4","space_id":"1d3d86fa67bef8c3","bk_skill_code":"redis-latency-diagnose","openclaw":{"category":"tencent","emoji":"🦈","requires":{"env":[]}}}
---

# Redis 集群延迟问题诊断

## Step 0：确认告警来源（用户说"延迟告警"时优先执行）

当用户说"延迟告警"但未指定具体集群时，先从 DBM 告警系统确认哪些集群有活跃告警，再逐集群诊断。

### 告警查询 API（bkdbm-mcp-prod-redis-query-alarm）

该 server 有 2 个工具：

| 工具 | 用途 | 参数 |
|------|------|------|
| `redis_query_alarm_fetch_app_alarms` | 按业务查告警（汇总） | `bk_biz_id`, `start_time`, `end_time` |
| `redis_query_alarm_fetch_cluster_alarms` | 按集群查告警 | `cluster_domain`, `start_time`, `end_time` |

**⚠️ 必须用 mcporter CLI + temp_config 调用，不能走 `patrol_compat.mcp_call`！**
（与 `bkdbm-mcp-prod-ticket-op` 相同的坑：patrol_compat 路由不覆盖此 server，调用返回空数据不报错。）

```bash
# 正确方式
mcporter call bkdbm-mcp-prod-redis-query-alarm.redis_query_alarm_fetch_app_alarms \
  --args '{"body_param": {"bk_biz_id": 900003, "start_time": "2026-07-17 16:00:00", "end_time": "2026-07-17 17:00:00"}}' \
  --config "$TEMP_CONFIG"
```

**返回数据结构**：
```json
{
  "unknown": {
    "<告警策略名>": [
      {
        "alert_name": "DBM#biz-11 Redis(TendisPlus)Proxy主机CPU使用率",
        "begin_time": 1784253720,  // Unix timestamp
        "description": "[TendisPlus]Proxy主机CPU使用率 >= 50.0, 当前值50.691866",
        "ip": "192.168.2.7",
        "tags": {
          "app": "biz-11",
          "appid": "900003",
          "cluster_domain": "tendisplus.example.db",
          "cluster_type": "PredixyTendisplusCluster",
          "instance_role": "proxy"
        },
        "target_key": "主机 192.168.2.7"
      }
    ]
  }
}
```

**关键点**：
- 数据嵌套在 `data["unknown"][<策略名>]` 下，不是扁平数组
- `begin_time` 是 Unix 时间戳（秒），不是字符串
- 延迟类告警的关键词：`耗时`（DBM 常用，如"访问耗时超过1秒"）、`延迟`、`latency`、`超时`、`timeout`、`慢`
- 时间窗口建议：先查最近 5 分钟，如为空扩大到 1 小时

**批量查所有业务告警**：
```bash
# 1. 先 list_my_bizs 获取所有 bk_biz_id
# 2. 逐业务调 fetch_app_alarms
# 3. 本地按 alert_name 过滤延迟类告警
# 4. 汇总受影响集群列表 → 进入 Step 1 逐集群诊断
```

---

## 诊断流程（六步，按顺序执行）

### Step 1：集群整体延迟趋势

拉 proxy 层延迟时序，确认延迟是持续高位还是阵发，以及大致从什么时间开始：

```
bkdbm-mcp-prod-redis-metrics.redis_metrics_query_cluster_proxy_series
  cluster_domains: [<cluster_domain>]
  metric_type: host_latency
  group_by: [cluster_domain]
  start_time / end_time: 问题时间范围前后各多1小时
  max_len_datapoints: 15
```

### Step 2：命令级延迟分析

确认哪类命令最慢，判断是特定命令（range scan 类：zrevrange/zcard）还是全命令慢：

```
bkdbm-mcp-prod-redis-metrics.redis_metrics_query_cluster_proxy_stats
  metric_type: command_latency
  group_by: [instance]   ← 注意：command_latency 不支持 bucket/cmd 分组
```

解析时按 `key = "<cmd>@<proxy_ip>:<port>"` 提取命令类型，按命令汇总 avg_ms。

**关键判断：**
- `zcard`/`zrevrange`/`zrevrangebyscore` 平均延迟异常高（数万 ms）→ TendisSSD range scan 问题
- 所有命令普遍慢 → 全局 IO 争抢（Compaction）
- 特定几个命令慢 → bigkey 或热 key 问题

### Step 3：Proxy 层分析（全局 vs 局部）⚡ 快速分流

> ⚡ **这一步是最关键的分流点**。先按 IP 拆 proxy 延迟：一旦发现单 proxy 极端高、其他 proxy 正常，就确认是「单 proxy 本地问题」，**可跳过 Step 4~5（master 侧）**，直接进入单 proxy 专项排查（连接数、进程、QPS 分配、客户端行为）。

```
bkdbm-mcp-prod-redis-metrics.redis_metrics_query_cluster_proxy_stats
  metric_type: host_latency
  group_by: [ip]
```

**判断逻辑：**
- 所有 proxy avg 延迟相近（差值 < 2x）→ 后端 master 整体问题，继续 Step 4
- **单 proxy max 极端高（> 100x 其他 proxy）+ 其他 proxy 完全正常** → **该 proxy 自身问题，直接跳到根因 6A/6B**
- **多个 proxy 异常但按机房分组**（同一机房全高，另一机房全正常）→ **Proxy→Master 网络分区抖动（根因11）**，需 mtr 验证
- 个别 proxy 延迟偏高但差距不极端 → 该 proxy 负载不均衡，继续 Step 4 同时排查该 proxy

> ⚠️ **注意**：同时检查各 proxy 的 QPS 分配是否均匀（用 `metric_type: qps` + `group_by: [ip]`）。若 QPS 比例与延迟比例吻合，说明是客户端连接分布不均导致负载集中。

#### Step 3 补充：按地区归属分组（排查网络区域因素）

若用户怀疑是某个机房/地区的网络问题，可通过 `redis_query_meta_list_cluster_proxies` 获取 proxy 的 `sub_zone` 字段（如「上海-富特」「上海-花桥」），再与延迟数据交叉分析：

```
bkdbm-mcp-prod-redis-query-meta.redis_query_meta_list_cluster_proxies
  body_param: { cluster_domain: "<domain>", page_size: 100, page: 1 }
```

返回字段包含：`address`（IP:Port）、`sub_zone`（机房地区）、`cls_name`（机型）、`status`、`version`。

**判断逻辑：**
- 某一个 `sub_zone` 延迟显著高于其他地区（> 3x）→ 该地区网络/机房问题
- 所有 `sub_zone` 延迟均高，只是程度不同 → **排除网络区域问题，是后端全局性故障**（2026-06-09 tendisplus-3.example.db 实测：5个地区全部高延迟 835-1561ms，确认是 master 超大 mget 导致）

### Step 4：Master 节点定位

```
bkdbm-mcp-prod-redis-metrics.redis_metrics_query_cluster_master_stats
  metric_type: host_latency
  group_by: [ip]
```

按 avg_ms 排序，找出明显高于其他节点的 IP。正常 master 延迟应在个位数~20ms，超过 50ms 需重点关注。

> ⚠️ **大 Key 场景必须下钻实例级**：IP 级 `group_by: ["ip"]` 是多实例均值，大 Key 只落在某个 IP 的特定端口（如 `:30001`），IP 级平均会掩盖单实例热点。当 Step 2/3 已指向特定命令（如 HMGET）且 IP 级延迟看似正常时，**必须补查实例级**：
> ```
> redis_metrics_query_cluster_master_stats
>   metric_type: qps / host_latency
>   group_by: ["instance"]   ← 关键！
> ```
> 找出 QPS 和延迟显著高于集群均值的实例（>3x QPS + >5x 延迟 = 大 Key 落盘实例）。
> CPU 不支持 instance group_by（只支持 ip/cluster_domain），需用 IP 级数据近似。

### Step 5：异常节点 QPS / CPU 综合分析

对 Step 4 找到的异常节点，并发拉三项指标做交叉分析：

```
bkdbm-mcp-prod-redis-metrics.redis_metrics_query_cluster_master_stats
  metric_type: qps / cpu_usage / host_latency
  group_by: [ip]
```

同时拉异常节点的实例级延迟时序（看是否持续或阵发）：

```
bkdbm-mcp-prod-redis-metrics.redis_metrics_query_instance_series
  instances: [{"ip": "<ip>", "port": <port>}]   ← 注意：instances 是对象数组
  metric_type: host_latency
  group_by: [instance]
  max_len_datapoints: 15
```

**判断模式：**

| 模式 | 含义 |
|------|------|
| 低 QPS + 高延迟 + 持续全天 | 节点自身 IO 问题（compaction / 硬件） |
| 高 QPS + 高延迟 + 高 CPU | 流量打满，需扩容或限流 |
| 阵发性延迟 + 特定时段 | 定时任务或业务高峰 |

### Step 6：慢日志验证

> ⚠️ **工具名勘误（2026-05-21 确认）**：`redis_query_log_get_cluster_slowlog_statics` 已不存在。
> 正确工具名：**`redis_query_log_query_slowlogs`**（`bkdbm-mcp-prod-redis-query-log` server）

**正确方式（mcporter CLI，2026-07-14 确认 `mcp_client.py` 已不存在）：**

```bash
mcporter call bkdbm-mcp-prod-redis-query-log.redis_query_log_query_slowlogs \
  --args '{"body_param": {"cluster_domain": "<domain>", "start_time": "<CST>", "end_time": "<CST+08:00>"}}'
```

> ⚠️ **如果当前用户的 mcporter 配置缺少该 server**，用 `MCPORTER_CONFIG` 指向拥有该 server 的用户配置：
> ```bash
> MCPORTER_CONFIG=/root/.dbm/mcporter/<other_user>/mcporter.json mcporter call bkdbm-mcp-prod-redis-query-log.redis_query_log_query_slowlogs ...
> ```
> **安全注意**：跨用户使用 MCPORTER_CONFIG 意味使用对方 auth token，仅用于查询类操作，绝不可用于写操作或越权操作。如对方 token 认证失败，必须停下告知用户，不可继续换其他用户重试。

**注意：** TendisSSD 的 slowlog queue 有限，真正卡 1000ms+ 的请求会刷掉慢日志队列，导致慢日志记录的只是"10~20ms 的轻度慢查询"。慢日志缺失 ≠ 没有慢查询，需结合 Step 5 的延迟指标综合判断。

**返回数据结构**（`redis_query_log_query_slowlogs` 实测格式）：
```json
{
  "data": {
    "by_instance": {
      "<ip:port>": {
        "duration_stats": { "avg_ms": 124.4, "max_ms": 222.3, "median_ms": 117.4, "min_ms": 100.2 },
        "slowest_query": { "cmd": "GET", "create_time": "2026-07-23T21:42:54+08:00", "duration_ms": 222.3, "key": "<key>" },
        "top_commands": { "GET": 20, "SET": 2 },
        "total_count": 22
      }
    },
    "summary": {
      "duration_stats": { "avg_ms": 104.5, "max_ms": 222.3, "median_ms": 117.4, "min_ms": 2.0 },
      "instance_count": 60,
      "top_commands": { "GET": 1152, "SET": 43, "HGET": 16 },
      "total_count": 1214
    }
  }
}
```

**解析时重点关注**：
- `summary` 先看整体：`instance_count`（受影响实例数）、`total_count`（总慢查数）、`top_commands`（命令分布）
- `by_instance` 按端口区分层级：`:50xxx` = Proxy 层，`:30xxx` = Master 层
  - Proxy 层 avg 100ms+ 而 Master 层 avg < 10ms → 问题在 Proxy→客户端链路，后端正常
  - Master 层 avg 也高（>20ms）→ 存储层有压力，需结合 Step 4/5 排查
- 按 `avg_ms` 降序排列实例，找最慢的 Proxy（通常是热点或网络问题实例）
- `slowest_query.key` 提取 Key 前缀，判断是否集中在同一业务前缀（热 Key 信号）
- 时间集中性：若所有 Proxy 的 `slowest_query.create_time` 集中在同一 20~30 秒窗口 → 全局性短暂波动（非持续问题）
- `11.x.x.x:30xxx` 端口段（同一物理机多实例）问题集中时，关注该机器的磁盘/网络健康

---

## Step 7（可选）：地区分布分析

当怀疑是网络/地区问题时，按 `bk_sub_zone` 分组对比 proxy 和 master 延迟：

### Proxy 地区分布

```python
# redis_query_meta_list_cluster_proxies 返回字段中直接含 sub_zone
args = {"body_param": {"cluster_domain": cluster, "page_size": 100, "page": 1}}
# 返回结构: data.proxies[].{address, sub_zone, cls_name, status, version}
# sub_zone 示例: "上海-富特", "上海-花桥", "上海-松江"
```

### Master 地区分布

proxy 接口不含 master 机器地区，需用 `dbmeta_query_list_machine_info` 反查：

```python
# 分批（每批 ≤ 15 个 IP）查机器信息
args = {"body_param": {"ips": ["ip1", "ip2", ...]}}
# server: bkdbm-mcp-prod-dbmeta-query
# tool:   dbmeta_query_list_machine_info
# 返回: data.machines[].{ip, bk_sub_zone, bk_idc_name, bk_idc_area, ...}
# 关键字段: bk_sub_zone（如"上海-花桥"）, bk_idc_name（如"昆山腾讯万国DC"）
```

**判断逻辑：**
- 所有地区延迟相近（差值 < 2x）→ 不是网络/地区问题，是后端存储层全局性问题
- 某一地区延迟极端高（> 3x 其他地区）→ 该地区到后端的网络路径有问题

> ⚠️ **实测陷阱（2026-06-09）**：`tendisplus-3.example.db` 案例中，46 个 proxy 分布在 5 个地区（上海-富特/宝信/松江/青浦/花桥），延迟 835-1561ms，各地区均值差仅 ~500ms（非数量级差异）→ 最终确认是网络问题而非存储层问题。地区分布分析是排除/确认网络因素的有效手段，但结论需结合业务侧信息综合判断。

## 参数注意事项（血泪坑）

详见 `references/api-params.md`

TendisSSD 读 IO 争抢全局慢案例（2026-06-18 ssd23.example.db） → `references/tendisssd-read-io-contention-2026-06-18.md`

### 关键参数陷阱（速查）

0. **告警查询 API 详细文档** → `references/alarm-query-api.md`
   含：数据结构、响应示例、延迟告警关键词、批量查询模式、fetch_cluster_alarms vs fetch_app_alarms 差异。

0.5 **根因速查表 + 完整决策树** → `references/root-cause.md`
   含：17 种根因模式详细识别特征 + 区分矩阵 + 决策树，文件顶部有目录。

0.8 **完整接口踩坑清单（25 条）** → `references/pitfalls.md`
   含：返回空数据、输出截断、参数限制、认证路由、指标口径误判五类问题的排查方式。

1. **`proxy_series` 和 `proxy_stats` 都需要 `cluster_domains`（复数，数组）**，不是 `cluster_domain`（单数字符串）。两者接口风格一致，不要混淆。
   ```json
   { "cluster_domains": ["cache13.example.db"] }   ✅
   { "cluster_domain": "cache13.example.db" }       ❌ → 报「该字段是必填项」
   ```
   `master_stats` 同样如此。

1.5. **所有 redis-metrics 工具参数必须包在 `body_param` 外层（2026-07-22 实测确认）**
   mcporter call 时，所有参数必须嵌套在 `body_param` 键下，不能直接平铺：
   ```json
   { "body_param": { "cluster_domains": [...], "metric_type": "host_latency", ... } }  ✅
   { "cluster_domains": [...], "metric_type": "host_latency", ... }                    ❌ → 报 "cluster_id or cluster_domain is required"
   ```
   **坑点**：直接传裸参数时错误信息是 "cluster_id or cluster_domain is required（8700500）"，
   看起来像是参数名错误，实际是缺少 `body_param` 包装。redis-query-meta、redis-query-log 等 server 同理。

2. **慢日志为空 ≠ 没有慢查询**（极端场景）：当集群延迟达到秒级（> 1000ms），slowlog 队列被高频慢请求持续刷新，记录的都是相对轻度的慢查询甚至全部被冲刷为空。此时应以 proxy/master `host_latency` 时序指标为准，慢日志结果不可信。2026-05-21 实测：`cache13` 告警值 2487ms，慢日志查询返回 0 条。

---

## 根因速查表

完整的 17 种根因识别特征、通用区分矩阵与决策树 → `references/root-cause.md`（含目录，按根因编号或关键词 grep 跳转）。

**按现象快速选择要读的根因**：

| 观察到的现象 | 候选根因 | 优先读 |
|---|---|---|
| Proxy 全部高、Master 也高、慢日志 `mget(subkey len:N)` | 超大 mget | 根因 8 |
| 慢日志 `HINCRBY`+`HGETALL` 集中同一 Key、单 Master CPU 35%+ | 超大 Hash | 根因 9 |
| 慢日志 `HMGET` 95%+、Master 延迟极低（<0.05ms） | TendisCache 热点 Hash | 根因 10 |
| 慢日志 `hgetall` 84%+、Master 极低、1~5min 自恢复 | TendisCache 短时告警 | 根因 14 |
| 慢日志 `XAUTOCLAIM` 97%+、内存线性增长 | Stream 消息积压 | 根因 15 |
| `hgetall` 10~20ms、Master 完全正常、持续数小时 | TendisSSD HGETALL 全局慢 | 根因 7 |
| `zcard`/`zrevrange` 极高、server log 有 compaction | Range Scan / IO 争抢 | 根因 1、2 |
| 慢日志 `hset`/`hincrby` 为主、多 Proxy 同时高、<10min 自恢复 | 写入洪峰 | 根因 17 |
| Proxy 按机房分组，部分秒级部分正常 | 网络分区抖动 | 根因 11 |
| 单 Proxy 极高、其余正常 | 单 proxy 阻塞 / 一过性尖刺 | 根因 6A、6B |
| 各 Proxy 连接均匀但 QPS 相差 5~6 倍 | Proxy QPS 分配不均 | 根因 13 |
| Pipeline 固定比例 key 间歇查不到、监控全正常 | hash-slot 集中 + 瞬时阻塞 | 根因 12 |
| 全集群 ~1s 基线 + 单节点极端尖刺 | 长期基线 + 尖刺 | 根因 16 |

**独立案例复盘**（含完整证据链与排查过程）：
- TendisSSD 读 IO 争抢全局慢（2026-06-18） → `references/tendisssd-read-io-contention-2026-06-18.md`
- TendisCache HMGET 热点 Hash（2026-06-30） → `references/tendiscache-hmget-hot-hash-2026-06-30.md`
- TendisCache HGETALL 短时告警（2026-07-19） → `references/tendiscache-hgetall-short-burst-2026-07-19.md`
- Proxy 机型分层不均（2026-07-14） → `references/proxy-machine-type-imbalance-2026-07-14.md`

---

## 告警持续性判断（一过性 vs 持续性）

**在开始逐步诊断前，先判断告警性质**，这决定了优先级和策略：

| 信号 | 一过性告警 | 持续性告警 |
|------|-----------|-----------|
| 告警持续时间 | < 5 分钟 | **> 15 分钟** |
| Proxy latest 延迟 | 已回落至正常（1~3ms） | 仍高位（> 10ms） |
| Proxy QPS latest | 接近 avg | **骤降（< 30% of avg）** |
| 慢日志时间分布 | 集中在特定时刻 | 跨越多个时间点持续 |
| 外部事件（Andon 通知） | 有基础设施事件（网络抖动等） | 无基础设施事件 |

**QPS latest 骤降（latest < 30% of avg）是重要信号**：
- 说明业务客户端已大量超时/报错，主动减少发送
- Proxy latest 延迟看起来"回落"实际是流量减少，不是问题自愈
- **必须同时确认 Master CPU/延迟已正常**才能判定恢复

### Andon 外部通知关联（2026-06-18 实战经验）

当多个集群同时出现短暂延迟尖刺并自恢复时，优先排查是否有基础设施层事件：

- **腾讯云上海六区网络抖动（2026-06-18 15:50:06~15:50:29）**同时触发了 `ssd23.example.db`（TwemproxyTendisSSDInstance）和 `ssd49.example.db`（PredixyTendisplusCluster）的延迟告警
- Andon Push 通知特征：发送方 `Andon Push(安灯ITSM Push)`，内容格式 `【紧急重要】【网络异常：已恢复】`
- 网络抖动导致的告警特征：
  1. 多集群同时触发（跨不同业务、不同集群类型）
  2. 告警首次时间与网络事件时间吻合（±2 分钟内）
  3. 慢日志集中在同一时刻（非跨时段持续）
  4. 所有 Proxy latest 延迟已正常，cv > 100 是窗口内历史尖刺的残影
  5. Master 层完全正常（Proxy→后端 无 IO 问题）

**Andon 通知到达通常比告警晚 3~10 分钟**，若告警触发时还没看到 Andon 通知，先把诊断跑完再对照时间线。

---

### 长期高延迟基线 + 瞬时尖刺触发告警（2026-08-03 实战归纳）

当发现**所有 Proxy 的 latest host_latency 均在 ~1s 且告警阈值为 512ms** 时，说明集群存在长期高延迟基线。此时需要区分两个独立问题，不能将尖刺节点当作唯一根因。

**诊断步骤**：
1. 拉昨天/前天同时段 `proxy_stats host_latency`（`group_by: ["cluster_domain"]`）对比 — 确认 ~1s 是否是长期基线（非今日新增）
2. 按 IP 分组找 `avg` 或 `max` 极端高的节点 — 该节点的尖刺是告警触发主因
3. 拉该异常节点的 QPS/connections/CPU 时序 — 确认尖刺性质（QPS burst? 连接骤增? 进程阻塞?）
4. 拉 Master 层 host_latency — 确认后端是否正常（若正常 = 问题在 Proxy 层）

**结论必须分两层**：
- **告警触发主因**：尖刺节点（如 192.168.2.9 QPS 4.5x burst → 延迟飙升 → 拉高集群平均值）
- **长期基线问题**：全集群 ~1s 延迟基线（可能架构限制：TendisSSD SSD IO + 跨可用区 Proxy→Master 网络延迟）

**QPS burst + connections 不变 = pipeline/batch 请求洪流**：少量连接发起大量请求（如 pipeline 批量操作），Proxy 请求队列积压导致延迟飙升。CPU 通常不达瓶颈（<35%），可快速自恢复。

**实战案例（2026-08-03 ssd142.example.db）**：
- 30 台 Proxy 全部 latest ~1s（昨天 8/2 同时段 avg=1127ms — **非今日新增，是长期基线**）
- 192.168.2.9 在 16:34 突发：QPS 2500→11203（4.5x），latency 1s→726s，CPU 32%，**connections 不变（2315）**
- 16:49:30 已恢复到 1014ms（latest 1196ms at 16:58:30）— 尖刺约 15 分钟
- Master 层完全正常（avg 45-76ms, CPU <18%, QPS 均衡 ~10000/节点）— 15-20x 延迟差距确认问题在 Proxy 层
- 全命令 latency 1s+：get 1188ms / hgetall 1460ms / set 10179ms / exists 1599ms — 全局性，非特定命令

---

## Pitfalls（接口与参数踩坑）

诊断中遇到接口报错、返回空数据、JSON 截断、指标与预期不符时 → `references/pitfalls.md`（25 条，含分类目录）。

**高频必知 4 条**（其余按需查阅参考文件）：

1. **所有 MCP 参数必须包在 `body_param` 外层**，否则报 `cluster_id or cluster_domain is required`。
2. **输出有 65536 bytes 硬限制**，`command_latency group_by=["ip"]` 极易截断 → 改用 `group_by=["cluster_domain"]` 或用 `ips` 参数缩小范围。
3. **时间必须带时区**（`2026-03-27T09:18:00+08:00`），禁止手动转 UTC；`proxy_series` 的 `end_time` 不得超前服务器时间 300 秒。
4. **IP 级 group_by 会掩盖实例级热点**——大 Key 只落到某 IP 的特定端口，IP 级是多实例均值。Master 看似正常时必须补查 `group_by=["instance"]`。
