# Oracle MCP Tools

Oracle 数据库相关的 MCP 工具集，供 LLM Agent 调用进行只读查询、健康探活、性能分析与 AWR 报告生成。

- **MCP server 名称**：`oracle-query`，`operation_id` 统一前缀 `oracle_query_`。
- **鉴权**：维度为实例所属集群（`bk_cloud_id` + `address`），`permission_classes=[McpClusterDetailPermission]` + `mcp_auth_parser=auth_parse_instances`。
- **元数据来源**：`db_meta.Machine` + `db_meta.Cluster`（`cluster_type` ∈ {`OraclePrimaryStandby`, `OracleSingleNone`}）+ `db_meta.StorageInstance`。
- **工具性质**：全部只读（SELECT / 只读包函数），使用绑定变量。
- **行数上限**：列表接口统一受 `ORACLE_MAX_ROWS`（默认 200）约束，以 `ROWNUM <= :row_limit` 子查询包装。
- **目标版本**：Oracle 11G。

## 通用入参

所有工具共享以下入参：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bk_cloud_id` | integer | 是 | 实例所在云区域 ID |
| `address` | string | 是 | 目标实例 `ip:port`；连接前校验实例存在且属于 Oracle 集群 |

## 环境变量

查询通过 DRS 的 `/v2/oracle/rpc` 接口执行（go-ora 纯 Go 驱动，无需 Oracle Instant Client，兼容11G）。

DBM（dbm-ui）侧：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ORACLE_SERVICE_NAME` | `CFDB` | 连接使用的 service_name |
| `ORACLE_ENABLE_AWR` | `true` | AWR / ASH 工具开关；未购买 Diagnostics Pack 时置为 `false` |
| `ORACLE_MCP_MAX_ROWS` | `200` | 单次查询返回行数上限 |
| `ORACLE_MCP_CONNECT_TIMEOUT` | `5` | DRS 建连超时（秒） |
| `ORACLE_MCP_QUERY_TIMEOUT` | `60` | 单条查询超时（秒） |
| `ORACLE_MCP_DISPLAY_TZ` | `+08:00` | 时间入参/出参的展示时区 |
| `ORACLE_MCP_ASH_MAX_LOOKBACK_DAYS` | `3` | 内存 ASH 最早回溯天数 |

## 工具目录（共 21 个）

| 能力域 | 工具数 | 用途 |
|---|---|---|
| 1. 状态探活 | 2 | 健康探活、告警日志 |
| 2. 会话与活动 | 3 | 活跃会话、阻塞链、长查询 |
| 3. 性能分析 | 5 | 执行计划（当前 / 历史）、内存 ASH 时间窗口分析（ASH 需开启） |
| 4. 历史 ASH | 4 | 过去时段的 AAS 曲线、wait class、Top 事件、Top SQL（需开启） |
| 5. 容量 | 3 | 表空间、Undo、SGA/PGA |
| 6. AWR | 4 | 快照清单、结构化负载指标、按快照/按时间生成报告（需开启） |

## 按时间选工具：实时 vs 历史

同一个问题（「慢在哪」）有两条链路，分界是内存 ASH 缓冲区的实际寿命，不是某个固定时长：

| | 实时链路 | 历史链路 |
|---|---|---|
| 数据源 | `v$session` + `v$active_session_history` | `dba_hist_active_sess_history` + `dba_hist_*` |
| 样本粒度 | 1 秒 | 10 秒 |
| 独有能力 | 活的会话、阻塞链、存活的游标 | 累计指标与基线、任意窗口曲线、已 age out 的 SQL 计划 |
| 入口 | `get_ash_wait_class` → `top_events` → `top_sql` → `get_sql_plan` | `get_awr_load_profile` → `get_ash_history_timeline` → `get_ash_history_*` → `get_sql_plan_awr` |

两侧都有数据时**优先实时**（粒度更细、能看到会话级信息）。移交信号已做进出参，按它判断而不是靠时长猜：

| 信号 | 含义与处置 |
|---|---|
| 实时侧 `coverage_sufficient=false` 或 `truncated=true` | 缓冲区已覆盖请求窗口前段 → 转历史链路 |
| 实时侧工具报错「超出内存 ASH 回溯上限」 | 同上 |
| 历史侧 `unflushed_sec > 0` | 请求终点尚未随快照落盘 → 该段转实时链路 |
| 历史侧报错「区间内没有已落盘的快照」 | 同上 |

---

## 1. 状态探活

### 1.1 `oracle_query_check_instance_status`

实例综合健康探活。一次调用完成：连通性检查、关键状态读取、会话上限使用率估算、DG 状态读取、探活耗时测量，并输出 `healthy / warning / critical` 等级与原因。

- **入参**：仅通用入参
- **数据源**：`v$instance`, `v$database`, `v$session`, `v$parameter`
- **判定规则**：
  - `critical`：实例非 `OPEN` / 数据库非 `ACTIVE` / `archiver=FAILED` / 实例 `blocked=YES`
  - `warning`：`logins=RESTRICTED` 或 session 使用率 ≥ 90%
  - 其它视为 `healthy`
- **`state` 字段**：取自 `v$instance` 的 `instance_name`, `host_name`, `version`, `startup_time`, `instance_status`, `database_status`, `instance_role`, `logins`, `archiver`, `active_state`, `blocked`；取自 `v$database` 的 `db_name`, `database_role`, `open_mode`, `protection_mode`, `protection_level`, `switchover_status`, `flashback_on`, `log_mode`。
- **出参**：

```json
{
  "reachable": true,
  "latency_ms": 32,
  "health": {
    "level": "warning",
    "reasons": ["logins=RESTRICTED"]
  },
  "state": {
    "instance_name": "orcl1",
    "startup_time": "2026-11-10T02:15:33+08:00",
    "instance_status": "OPEN",
    "database_status": "ACTIVE",
    "database_role": "PRIMARY",
    "open_mode": "READ WRITE",
    "protection_mode": "MAXIMUM PERFORMANCE",
    "switchover_status": "TO STANDBY",
    "archiver": "STARTED",
    "logins": "RESTRICTED",
    "blocked": "FALSE"
  },
  "sessions": {
    "total_sessions": 180,
    "active_sessions": 12,
    "blocked_sessions": 0,
    "user_sessions": 150,
    "session_limit": 500,
    "session_usage_pct": 36.0
  }
}
```

- 连接失败时返回 `reachable=false`、`health.level=critical`，`state` / `sessions` 为空对象。

### 1.2 `oracle_query_get_alert_log_errors`

查询近 N 分钟告警日志中的 ORA 错误（`v$diag_alert_ext`，`message_level <= 16`），在数据库侧按错误码聚合。

- **入参**：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `minutes` | int | 否 | 120 | 回溯分钟数（1-4320） |
| `limit` | int | 否 | `ORACLE_MAX_ROWS` | 错误码个数上限 |

- **出参**：

```json
{
  "errors": [
    {
      "error_code": "ORA-00600",
      "occurrences": 3,
      "first_seen": "2026-11-17T09:12:04+08:00",
      "last_seen": "2026-11-17T10:40:01+08:00",
      "sample_text": "ORA-00600: internal error code, arguments: [kcbz_check_objd_typ_3], ..."
    }
  ],
  "count": 1,
  "minutes": 120
}
```

| 字段 | 说明 |
|---|---|
| `error_code` | 每条消息中第一个 `ORA-`，补零为 5 位（告警日志中 `ORA-1652` / `ORA-01652` 两种写法都有） |
| `occurrences` | 窗口内该错误码出现的消息条数 |
| `first_seen` / `last_seen` | 首次 / 最近出现时间 |
| `sample_text` | 该错误码最近一次出现的消息，含 trace 文件路径等定位信息，截断到 500 字符 |
| `count` | 去重后的错误码个数，不是消息总条数 |

- 一条消息含多个 ORA 错误码时只取第一个。
- 不含 ORA 错误的消息（日志切换、实例启停等）不在返回范围内。

---

## 2. 会话与活动

> 本节三个工具均带出 `child_number`（`v$session.sql_child_number`）。`sql_id` 只定位 SQL 文本，
> **`sql_id` + `child_number` 才唯一定位一个游标**，可直接作为 `get_sql_plan` 的 `child_number` 入参。

### 2.1 `oracle_query_get_active_sessions`

查询活跃用户会话（`v$session.status='ACTIVE'` 且 `wait_class != 'Idle'`）。

- **入参**：`limit`（默认 `ORACLE_MAX_ROWS`）
- **出参**：`{"sessions": [...], "count": N}`
- **关键列**：`sid`, `serial_num`, `username`, `sql_id`, `child_number`, `event`, `wait_class`, `seconds_in_wait`, `blocking_session`, `last_call_et`

### 2.2 `oracle_query_get_blocking_sessions`

查询阻塞链（blocker → waiter），按 `waiter.seconds_in_wait` 降序。

- **入参**：`limit`
- **出参**：`{"blocking_chains": [...], "count": N}`
- **关键列**：`blocker_sid`, `blocker_user`, `blocker_sql_id`, `blocker_child_number`, `waiter_sid`, `waiter_user`, `waiter_sql_id`, `waiter_child_number`, `waiter_event`, `waiter_seconds_in_wait`

### 2.3 `oracle_query_get_long_running_queries`

查询长时间运行的 SQL（`v$session.last_call_et >= min_seconds`）。

- **入参**：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `min_seconds` | int | 否 | 60 | 最小运行时长（秒） |
| `limit` | int | 否 | `ORACLE_MAX_ROWS` | 返回行数上限 |

- **出参**：`{"queries": [...], "count": N}`
- **关键列**：`sid`, `username`, `sql_id`, `child_number`, `seconds_running`, `event`, `sql_text`

---

## 3. 性能分析

### 3.1 `oracle_query_get_sql_plan`

查询指定 `sql_id` 的**当前**执行计划（`DBMS_XPLAN.DISPLAY_CURSOR`，固定 `ALL` 格式），返回 Oracle 官方格式化文本：带缩进的执行树、Predicate Information、Column Projection、Note 段。

- **入参**：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `sql_id` | string | 是 | — | SQL ID，白名单校验（字母/数字/下划线） |
| `child_number` | int | 否 | null | 子游标号；**不传则输出全部子游标**（显式传 `NULL`，避免 `DISPLAY_CURSOR` 默认只输出 child 0） |

- **出参**：

```json
{
  "sql_id": "a1b2c3d4e5f6g",
  "found": true,
  "plan_text": "Plan hash value: 1234567890\n\n| Id | Operation | ...",
  "line_count": 42,
  "warnings": []
}
```

- `found=false` 表示游标已不在共享池中，此时 `warnings` 直接指向 `get_sql_plan_awr`；文本行数上限 `ORACLE_XPLAN_MAX_LINES`（2000）。

### 3.2 `oracle_query_get_sql_plan_awr`

查询指定 `sql_id` 的**历史**执行计划（`DBMS_XPLAN.DISPLAY_AWR`，读 `dba_hist_sql_plan`），不依赖共享池，是历史分析链路的终点。

- **入参**：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `sql_id` | string | 是 | — | 同上，白名单校验 |
| `plan_hash_value` | int | 否 | null | 取自 `get_ash_history_top_sql` / `get_ash_top_sql` 的 `top_plan_hash_value`；不传则输出该 SQL 的全部历史计划 |

> **定位维度是 `plan_hash_value`，不是 `child_number`。** 子游标是内存概念，历史快照中不存在，
> 两个工具的第二个入参不可互换。

- **出参**：

```json
{
  "sql_id": "a1b2c3d4e5f6g",
  "plan_hash_value": 1234567890,
  "found": true,
  "plan_text": "...",
  "line_count": 58,
  "plan_hash_values": [1234567890, 987654321],
  "plans": [
    {"plan_hash_value": 1234567890, "first_seen": "...", "last_seen": "..."}
  ],
  "warnings": []
}
```

| 字段 | 说明 |
|---|---|
| `plan_hash_values` | 该 `sql_id` 在 AWR 中留存的全部计划；长度 > 1 即期间发生过计划变更 |
| `plans` | 每个计划的 `first_seen` / `last_seen`，用于定位计划变更发生的时点 |

- `found=false` 且 `plan_hash_values` 非空 → 传入的 `plan_hash_value` 不对，省略该参数重试；
- `found=false` 且 `plan_hash_values` 为空 → 该 SQL 未被 AWR 采集（未进入 Top SQL）或已超出保留期。

### 3.3 ASH 时间窗口分析（3 个工具，开关控制）

`oracle_query_get_ash_wait_class` / `oracle_query_get_ash_top_events` / `oracle_query_get_ash_top_sql`。

基于 `v$active_session_history`，统计指定时间区间 `[begin_time, end_time]` 内前台会话的 DB time（1 个样本 ≈ 1 秒）。
ASH 与 AWR 同属 Diagnostics Pack，共用 `ORACLE_ENABLE_AWR` 开关；置为 `false` 时返回「功能未启用」。

- 数据源**只有内存 ASH**（`v$active_session_history`），不查 `dba_hist_active_sess_history`；更早的时段交给第 4 节的历史 ASH 工具。
- 只接受绝对时间区间，不提供「最近 N 分钟」入参；相对描述由调用方换算为绝对区间。
- 建议下钻顺序：`get_ash_wait_class`（定方向）→ `get_ash_top_events`（定事件）→ `get_ash_top_sql`（定 SQL）→ `get_sql_plan`。

- **公共入参**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `begin_time` | string | 是 | 起始时间，ISO 8601 带时区偏移（例 `2026-11-18T11:07:34+08:00`） |
| `end_time` | string | 是 | 结束时间，格式同上，须晚于 `begin_time` |
| `limit` | int | 否 | 仅 `top_events` / `top_sql`，默认 20 / 15 |

#### 时间口径

入参与出参的时间均为 ISO 8601 带时区偏移（`YYYY-MM-DDTHH:MM:SS±HH:MM`）：

- 入参层（`OracleTimeWindowMixin`）校验必须带偏移，缺省时区直接报错；
- `sample_time` / `end_interval_time` / `SYSDATE` 为不带时区的服务器本地时间，SQL 侧先转到数据库服务器时区再比较（`helpers/time_window.py`）；
- 出参用 `FROM_TZ(..., 服务器偏移)` 渲染回带偏移的 ISO 8601，可直接回填为下一次调用的入参；
- `end_time` 略晚于当前时刻时自动收敛到 `db_now`。

#### 窗口限制

超限即报错，由调用方改走第 4 节的历史 ASH 工具（`get_ash_history_*`）：

| 限制 | 默认值 | 常量 | 校验位置 |
|---|---|---|---|
| 最早回溯 | 3 天 | `ORACLE_ASH_MAX_LOOKBACK_DAYS`（env `ORACLE_MCP_ASH_MAX_LOOKBACK_DAYS`） | impl 层，按窗口查询返回的 `lookback_sec`（由 `SYSDATE` 算出）判定 |
| 单次跨度 | 6 小时 | `ORACLE_ASH_MAX_SPAN_HOURS` | 入参层（`OracleTimeWindowMixin`） |

> 回溯上限只是硬限制。缓冲区的**实际**寿命通常远短于 3 天，由 `coverage_sufficient` 兜底判断，
> 不要把 3 天当作「3 天内都查得到」。

#### 出参 `window`（完整版，`get_ash_wait_class`）

| 字段 | 说明 |
|---|---|
| `requested_begin_time` / `requested_end_time` | 请求区间回显 |
| `db_now` | 查询时的数据库时间（`SYSDATE`，带服务器时区偏移） |
| `actual_begin` / `actual_end` | 实际统计区间：起点为 `max(begin_time, oldest_sample_time)`，终点为 `min(end_time, db_now)` |
| `oldest_sample_time` / `latest_sample_time` | 内存 ASH 缓冲区当前覆盖的样本范围 |
| `requested_sec` | `actual_end - begin_time`，本次「本应统计」的秒数（已剔除超出当前时刻的部分） |
| `effective_sec` | `actual_end - actual_begin`，实际有样本覆盖的秒数；`aas` 一律按它计算 |
| `coverage_pct` | `effective_sec / requested_sec * 100` |
| `coverage_sufficient` | `coverage_pct >= ORACLE_ASH_MIN_COVERAGE_PCT`（90）；**false 时应改走历史 ASH** |
| `truncated` | 实际窗口比应统计窗口短超过 60 秒，即前段已被循环缓冲区覆盖 |
| `warnings` | 降级原因（ASH 覆盖不足、`end_time` 超出当前时刻等） |
| `total_samples` | 原始样本数，`sample_sufficient` 的判定依据 |
| `sample_interval_sec` | 固定 1，与历史 ASH 的 10 对应 |
| `total_db_time_sec` / `total_aas` | 窗口内全部前台会话的 DB time 与整体 AAS |
| `cpu_db_time_sec` | 其中 `session_state='ON CPU'` 的部分 |
| `load` / `activity` | CPU 繁忙度与活跃度分级，见下文 |

`total_db_time_sec` / `total_aas` / `cpu_db_time_sec` 不受 `limit` 截断影响。

#### 出参 `window`（精简版，`get_ash_top_events` / `get_ash_top_sql`）

`load` / `activity` 等整体判定只在 `get_ash_wait_class` 中返回。内存 ASH 为循环缓冲区，同一请求区间在不同时刻调用得到的
`actual_begin` / `effective_sec` 可能不同，各行 `aas` / `pct` 按本次调用自身的 `effective_sec` 与样本总数计算，故精简版保留以下字段：

| 字段 | 说明 |
|---|---|
| `actual_begin` / `actual_end` | 本次实际统计区间 |
| `effective_sec` | 本次实际有样本覆盖的秒数，`aas` 按它计算 |
| `coverage_pct` / `coverage_sufficient` / `truncated` | 同完整版 |
| `sample_sufficient` | 取自完整版 `activity.sample_sufficient` |
| `total_db_time_sec` | 本次窗口内全部前台样本数 |
| `warnings` | 同完整版 |

#### `window.load`：CPU 繁忙度分级

`AAS = AAS(ON CPU) + AAS(等待)`，只有 ON CPU 部分能与 `cpu_count` 对比，因此 `level` 只由 `aas_cpu / cpu_count` 决定。
`cpu_count` 随窗口查询以标量子查询一并取回，不增加 DRS 往返。

| 字段 | 说明 |
|---|---|
| `cpu_count` | 实例 `cpu_count` 初始化参数；取不到或非正数时为 `null` |
| `aas_cpu` | `ON CPU` 部分的 AAS |
| `aas_wait` | `total_aas - aas_cpu`，等待部分的 AAS |
| `aas_cpu_per_core` | `aas_cpu / cpu_count`，即 CPU 繁忙度 |
| `wait_dominant` | 等待 AAS ≥ CPU AAS 且 ≥ 1.0 时为 `true`，表示瓶颈不在 CPU |
| `level` | `low` / `normal` / `high` / `critical` / `unknown` |
| `summary` | 上述判定的文字说明，含算式与等待占主导时的提示 |

| `aas_cpu_per_core` | `level` | 含义 |
|---|---|---|
| < 0.5 | `low` | CPU 仍有明显余量 |
| 0.5 – 0.8 | `normal` | ON CPU 会话数接近 CPU 核数 |
| 0.8 – 1.2 | `high` | ON CPU 会话数超过 CPU 核数，CPU 上存在排队 |
| ≥ 1.2 | `critical` | 远超 CPU 核数 |

`level` 低不代表没有问题：`aas_cpu_per_core` 低而 `total_aas` 高，说明并发高但不烧 CPU，时间花在等待上，
此时 `aas_wait` 会明显大于 `aas_cpu`，需结合 `wait_class` 判断瓶颈归属。

#### `window.activity`：活跃度分级

用 `total_aas`（CPU + 全部非空闲等待）回答「数据库忙不忙」，与 `load` 正交。
ASH 只采样活跃会话，`SQL*Net message from client` 等空闲等待不进入样本，故 `total_aas` 低即数据库确实没在干活。

| 字段 | 含义 |
|---|---|
| `level` | `idle` / `light` / `active` / `unknown` |
| `peak_minute` | 窗口内样本最多的一分钟（ISO 8601 带时区，精确到分钟） |
| `peak_minute_aas` | 该分钟的 AAS |
| `peak_bucket_sec` | 峰值桶长度（内存 ASH 为 60） |
| `bursty` | 峰值桶 AAS ≥ 1.0 且 ≥ 3 倍 `total_aas` 时为 `true`，表示突发被平均值掩盖 |
| `sample_sufficient` | 样本数是否 ≥ `min_samples_for_pct`（60） |
| `min_samples_for_pct` | 占比结论所需的最少样本数 |
| `summary` | 上述判定的文字说明，前缀为实际统计区间，并追加突发与样本不足提示 |

| `level` | 条件 |
|---|---|
| `idle` | `total_aas < 0.1` 且 `peak_minute_aas < 1` |
| `light` | `total_aas < 1` |
| `active` | 其他 |

- `peak_minute_aas` 远高于 `total_aas` 时（即 `bursty=true`），说明负载集中在个别分钟、被区间平均值掩盖，宜缩小窗口重查。
- `sample_sufficient=false` 时，`wait_classes` / `events` / `top_sql` 中的 `pct` 由极少样本算出，不具统计意义。
  注意这不代表数据源不可用（空闲时段样本本来就少），换数据源同样少，故不应据此改走历史 ASH。

#### 各工具列表出参

统一口径：`session_state='ON CPU'` 的样本，event 记为 `CPU + CPU Wait`，wait_class 记为 `CPU`。

列表行里的 `samples` 是原始样本数，`db_time_sec = samples × sample_interval_sec`。内存 ASH 的倍率为 1，
故两列数值相同（保留 `samples` 是为了与历史 ASH 的行结构一致，也便于判断该行的统计显著性）。

| 工具 | 列表字段 | 关键列 |
|---|---|---|
| `oracle_query_get_ash_wait_class` | `wait_classes` | `wait_class`, `samples`, `db_time_sec`, `aas`, `pct` |
| `oracle_query_get_ash_top_events` | `events` | `event`, `wait_class`, `samples`, `db_time_sec`, `aas`, `pct`, `pct_cum`, `sessions`, `top_sql_id`, `top_sql_sec` |
| `oracle_query_get_ash_top_sql` | `top_sql` | `sql_id`, `samples`, `db_time_sec`, `aas`, `pct_of_sql_time`, `pct_of_db_time`, `top_event`, `top_event_pct`, `plan_count`, `top_plan_hash_value`, `top_child_number`, `sql_text` |

`get_ash_top_sql` 补充说明：

- `pct_of_sql_time` 为占「有 sql_id 的样本」比例，`pct_of_db_time` 为占全部前台样本比例；
- `plan_count` 按窗口内不同 `sql_plan_hash_value` 去重计数，`> 1` 表示窗口内同一 SQL 使用了多个执行计划；
- `top_plan_hash_value` 与 `top_child_number` 取自同一行，描述同一个游标。排序先排除 `plan_hash_value=0`（样本未关联到计划）再按样本数降序，故只有该 SQL 全部样本都无计划时 `top_plan_hash_value` 才为 `null`；
- 该 `child_number` 来自采样时刻，`get_sql_plan` 查不到计划时省略它重试；
- `sql_text` 优先取 `v$sqlstats`，已被挤出共享池时回退 `dba_hist_sqltext`。

#### 调用方（skill）建议流程

1. 先取数据库当前时间（`check_instance_status` 输出，或任意窗口查询的 `db_now`），把用户的时间描述换算成绝对区间；
2. 区间早于 3 天前或跨度超过 6 小时 → 直接走第 4 节历史 ASH；
3. 否则调 `get_ash_wait_class`，命中以下任一条件即改走历史 ASH：工具报错、`coverage_sufficient=false`；`activity.sample_sufficient=false` 时不要改走历史（样本少说明数据库确实空闲，换数据源也一样少），只是不能据 `pct` 下结论；
4. ASH 可用时按 `top_events` → `top_sql` → `get_sql_plan` 下钻（`top_events` / `top_sql` 可并行），CPU 繁忙度与活跃度只取 `get_ash_wait_class` 的 `window.load` / `window.activity`，各工具的精简 `window` 仍需检查 `coverage_sufficient` / `sample_sufficient`；
5. 结论中注明本次依据的是内存 ASH 还是历史 ASH——退到历史侧后，会话级、阻塞链不可用，样本粒度降为 10 秒。

---

## 4. 历史 ASH（开关控制）

> **开关**：与 AWR 共用 `ORACLE_ENABLE_AWR`（同属 Diagnostics Pack，且同一数据管道、同一保留期）。

数据源 `dba_hist_active_sess_history`，回答「过去某时段慢在哪」。与第 3 节内存 ASH 的出参结构、字段名、判定阈值全部对齐（判定逻辑集中在 `helpers/ash_window.py`，两边共用），因此两条链路的结论可以直接衔接。

### 三个必须知道的口径差异

| 差异 | 说明 |
|---|---|
| **1 个样本 = 10 秒** | MMON 每 10 秒从内存 ASH 抽一个样本落盘。`db_time_sec` 已按该倍率换算；但 `sample_sufficient` 按**原始样本数**（出参 `total_samples`）判定，不乘倍率——否则 6 个样本就会被当成统计有效 |
| **窗口终点是最新快照，不是 `SYSDATE`** | 视图是 `WRH$_ACTIVE_SESSION_HISTORY` 与 `WRM$_SNAPSHOT` 的 join，未随快照落盘的样本不可见。缺口由 `unflushed_sec` 给出 |
| **必须带 `snap_id` 区间** | 底层表按 `(dbid, snap_id)` 范围分区。impl 先解析时间区间为 `snap_id` 区间并以字面量带入 SQL，确保分区裁剪静态生效；只按 `sample_time` 过滤会扫全部历史分区 |

### 公共入参

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `begin_time` / `end_time` | string | 是 | ISO 8601 带时区偏移，时间口径同 3.3 |
| `limit` | int | 否 | 仅 `top_events` / `top_sql`，默认 20 / 15 |

### 窗口限制

| 限制 | 默认值 | 常量 |
|---|---|---|
| 单次跨度 | 24 小时 | `ORACLE_HIST_ASH_MAX_SPAN_HOURS`，与 AWR 对齐 |

回溯范围不单独校验：能查到多久完全取决于 AWR 实际保留期。请求起点早于保留期时，
`coverage_pct` 会自然偏低并触发 `coverage_sufficient=false`，比校验配置值更准确。

### 出参 `window` 在内存版之外新增的字段

| 字段 | 说明 |
|---|---|
| `sample_interval_sec` | 固定 10，提示换算倍率 |
| `unflushed_sec` | 请求终点晚于最新快照的秒数；**> 0 时该段需改用内存 ASH** |
| `first_sample_time` / `last_sample_time` | 窗口内实际样本的首尾时刻 |
| `oldest_snap_time` / `newest_snap_time` | AWR 仓库覆盖的快照时间范围 |
| `snap_lo` / `snap_hi` | 本次实际扫描的快照区间 |
| `snap_interval_min` | 实例的快照采集间隔（分钟） |
| `activity.peak_bucket` / `peak_bucket_aas` | 峰值桶为 **5 分钟**粒度（10 秒一个样本，1 分钟桶抖动过大），字段名也相应为 `peak_bucket` 而非 `peak_minute` |

`coverage_sufficient=false` 在历史侧的含义是「请求起点早于 AWR 保留期」，而非缓冲区被覆盖。

### 4.1 `oracle_query_get_ash_history_timeline`

历史时段的 AAS 时间曲线，**用于定位被区间平均值掩盖的尖峰**。

这是 AWR 报告做不到的事：1 小时快照里「10 分钟 AAS=4、其余 50 分钟 AAS=0.4」与「全程 AAS=1.0」在报告上完全一样，而用户投诉的就是那 10 分钟。

- **额外入参**：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `bucket_minutes` | int | 否 | 自动 | 可选 `1 / 5 / 15 / 30 / 60`；不传则自动选最细且行数 ≤ `ORACLE_MAX_ROWS` 的粒度 |

- **出参**：`{"window": {...}, "timeline": [...], "count": N}`
- **列表关键列**：`bucket_begin`, `samples`, `db_time_sec`, `aas`（按桶长计算，**不是**按 `effective_sec`）, `aas_cpu`, `top_wait_class`, `top_wait_pct`
- **`window` 额外字段**：

| 字段 | 说明 |
|---|---|
| `bucket_minutes` | 实际使用的分桶粒度 |
| `bucket_count` / `expected_bucket_count` | 两者之差即无活跃样本的空闲桶数（空桶不出现在序列中，这本身是有效信息） |
| `total_aas` | 窗口整体平均；与各桶 `aas` 对比即可量化尖峰被平均掩盖的程度 |

显式指定的 `bucket_minutes` 会使行数超限时直接报错（而不是静默截断尾部时段）。

### 4.2 `oracle_query_get_ash_history_wait_class`

历史时段 DB time 按 `wait_class` 汇总，含 `load` / `activity` 分级。

- **出参**：`{"window": {...完整版}, "wait_classes": [...], "count": N}`
- **关键列**：`wait_class`, `samples`, `db_time_sec`, `aas`, `pct`

### 4.3 `oracle_query_get_ash_history_top_events`

- **出参**：`{"window": {...精简版}, "events": [...], "count": N}`
- **关键列**：`event`, `wait_class`, `samples`, `db_time_sec`, `aas`, `pct`, `pct_cum`, `sessions`, `top_sql_id`, `top_sql_sec`

### 4.4 `oracle_query_get_ash_history_top_sql`

- **出参**：`{"window": {...精简版}, "top_sql": [...], "count": N}`
- **关键列**：`sql_id`, `samples`, `db_time_sec`, `aas`, `pct_of_sql_time`, `pct_of_db_time`, `top_event`, `top_event_pct`, `plan_count`, `top_plan_hash_value`, `sql_text`

与内存版的两处差异：

- **不返回 `child_number`**（历史快照中没有子游标概念）。下一步用 `sql_id` + `top_plan_hash_value` 调 `get_sql_plan_awr`，不要拿 `plan_hash_value` 去填 `get_sql_plan` 的 `child_number`；
- `sql_text` 优先取 `dba_hist_sqltext`，取不到再回退 `v$sqlstats`（与内存版的优先级相反）。

---

## 5. 容量

### 5.1 `oracle_query_get_tablespace_usage`

表空间使用率，按已用占比降序。

- **入参**：`limit`
- **数据源**：`dba_data_files` + `dba_free_space`
- **出参**：`{"tablespaces": [...], "count": N}`
- **关键列**：`tablespace_name`, `total_mb`, `used_mb`, `free_mb`, `used_pct`, `max_mb`, `autoextensible`

### 5.2 `oracle_query_get_undo_usage`

Undo 表空间使用情况（按 `ACTIVE` / `UNEXPIRED` / `EXPIRED` 分组）。

- **入参**：仅通用入参
- **数据源**：`dba_undo_extents`
- **出参**：`{"undo_extents": [...]}`

### 5.3 `oracle_query_get_sga_pga_usage`

SGA / PGA 内存使用情况。

- **入参**：仅通用入参
- **数据源**：`v$sga`, `v$pgastat`
- **出参**：`{"sga": [...], "pga": [...]}`

---

## 6. AWR（开关控制）

> **开关**：`ORACLE_ENABLE_AWR`，默认 `true`；置为 `false` 时所有 AWR 工具抛 `DBMMcpFeatureDisabledException`。

本节 4 个工具分两类，**不要混用**：

| 工具 | 返回 | 调用方式 |
|---|---|---|
| `list_awr_snapshots` / `get_awr_load_profile` | 结构化 JSON，几 KB | 模型可直接 tool call |
| `generate_awr_report` / `generate_awr_report_by_time` | 完整报告文本，200KB–2MB | **必须由 skill 的脚本 / CLI 调用并裁剪**，禁止模型直接 tool call |

> ⚠️ `generate_awr_report` / `generate_awr_report_by_time` 的返回值会直接进入模型上下文。
> MCP 侧只取回完整原始报告，不做裁剪。

**巡检与基线对比用 `get_awr_load_profile`，不要用报告文本。** 报告只给单个区间的聚合值，无法回答「是否偏离正常水平」；`get_awr_load_profile` 给的是逐快照序列，既能看走势，也能把另一时段的同结构结果直接拿来对比。只有需要报告独有的明细（表空间 I/O、Segment 级统计、Instance Efficiency 各类命中率）时才生成报告。

### 6.1 `oracle_query_list_awr_snapshots`

列出最近 N 天的 AWR 快照（`dba_hist_snapshot`，固定当前 `dbid` + `instance_number`）。

- **入参**：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `days` | int | 否 | 7 | 回溯天数（1-90） |
| `limit` | int | 否 | `ORACLE_MAX_ROWS` | 返回行数上限 |

- **出参**：`{"snapshots": [...], "count": N, "days": 7}`
- **关键列**：

| 字段 | 说明 |
|---|---|
| `snap_id` | 快照 ID，按降序返回 |
| `begin_interval_time` / `end_interval_time` | 快照区间 |
| `interval_sec` | 快照间隔秒数；明显大于实例的 `snap_interval` 即存在采集缺口 |

做历史分析前先用它确认目标时段的快照是否连续。

### 6.2 `oracle_query_generate_awr_report`

生成指定快照区间 `[begin_snap, end_snap]` 的 AWR 报告（`dbms_workload_repository.awr_report_text/html`）。

- **入参**：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `begin_snap` | int | 是 | — | 起始快照 ID |
| `end_snap` | int | 是 | — | 结束快照 ID（必须 > `begin_snap`） |
| `format` | string | 否 | `text` | `text` 供 LLM 分析 / `html` 供人工查看 |

- **出参**：

```json
{
  "begin_snap": 1000,
  "end_snap": 1001,
  "format": "text",
  "report": "WORKLOAD REPOSITORY report for ...",
  "report_size": 132480,
  "truncated": false,
  "warnings": []
}
```

- 报告固定针对**当前实例**：`dbid` / `instance_number` 取自 `v$database` / `v$instance`，不支持指定，也不在出参中回显。
- **`truncated`**：报告由 pipelined function 按行返回，不受 `ORACLE_MAX_ROWS` 约束，但受 `ORACLE_AWR_MAX_LINES`约束；触达上限时内容被静默截断，此时 `truncated=true` 并在 `warnings` 中给出提示。

### 6.3 `oracle_query_generate_awr_report_by_time`

按时间区间生成 AWR 报告：自动把 `[begin_time, end_time]` 解析为快照区间，免去先查 `snap_id` 的步骤。

- **入参**：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `begin_time` | string | 是 | — | ISO 8601 带时区偏移（例 `2026-11-18T11:07:34+08:00`） |
| `end_time` | string | 是 | — | 格式同上，须晚于 `begin_time` |
| `format` | string | 否 | `text` | 同 6.2 |

- **时间口径**：与 ASH 工具一致，见 3.3「时间口径」。
- **跨度上限**：24 小时（`ORACLE_AWR_MAX_SPAN_HOURS`）。跨度过大时各项统计被平均稀释，失去诊断价值。
- **执行顺序**：先解析并校验快照区间，再生成报告。快照参数不匹配时 `awr_report_*` 不报错、只返回空报告，故必须前置校验。

#### 快照选择策略：外扩

| 边界 | 取法 |
|---|---|
| `begin_snap` | `end_interval_time <= begin_time` 中 `snap_id` 最大者 |
| `end_snap` | `end_interval_time >= end_time` 中 `snap_id` 最小者 |

即报告区间 ⊇ 请求区间，保证请求时段被完整覆盖，且窗口短于快照间隔（默认 1 小时）时仍可工作。

- **出参**：在 6.2 的字段之外追加（实际区间可能宽于请求区间，故回显）：

```json
{
  "requested_begin_time": "2026-11-16T04:30:00+08:00",
  "requested_end_time":   "2026-11-16T06:30:00+08:00",
  "actual_begin_snap":    1000,
  "actual_end_snap":      1003,
  "actual_begin_time":    "2026-11-16T04:00:40+08:00",
  "actual_end_time":      "2026-11-16T07:00:14+08:00"
}
```

`actual_begin_snap` / `actual_end_snap` 与 `begin_snap` / `end_snap` 取值相同，单独回显便于与 `actual_*_time` 对照，
也便于调用方拿这对 `snap_id` 直接调 `generate_awr_report` 换格式重新生成。

#### 边界情况

| 情况 | 处理 |
|---|---|
| 仓库内无任何快照 | 报错（AWR 未采集或刚建库） |
| `begin_time` 早于最早快照 | 报错并给出最早快照 `snap_id` 与时刻（超出保留期，默认 8 天） |
| `end_time` 晚于最新快照 | 回退到最新快照 + `warnings`，并提示改用 ASH 分析该时刻之后的活动 |
| 回退后区间内仍无完整快照间隔 | 报错并提示等待下一次快照或改用 ASH |

### 6.4 `oracle_query_get_awr_load_profile`

按快照逐段输出负载指标序列，数据源 `dba_hist_sys_time_model` + `dba_hist_sysstat` 的增量。**巡检与基线对比的主入口**，返回结构化 JSON（通常几 KB），模型可直接调用。

- **入参**：`begin_time` / `end_time`（口径与跨度上限同 6.3）
- **快照区间**：复用 6.3 的外扩策略。`begin_snap` 只作为求差的基线，本身不产生数据行，故数据行数 = 快照对数。
- **出参**：

```json
{
  "requested_begin_time": "2026-11-20T09:00:00+08:00",
  "requested_end_time":   "2026-11-20T12:00:00+08:00",
  "actual_begin_snap": 1000,
  "actual_end_snap":   1003,
  "actual_begin_time": "2026-11-20T09:00:12+08:00",
  "actual_end_time":   "2026-11-20T12:00:08+08:00",
  "snapshot_count": 3,
  "profile": [
    {"snap_id": 1001, "begin_time": "...", "end_time": "...", "interval_sec": 3600,
     "db_time_sec": 3721.4, "aas": 1.03, "hard_parse_pct": 0.8}
  ],
  "warnings": []
}
```

- **`profile[]` 指标**：

| 分组 | 字段 |
|---|---|
| 时间模型 | `db_time_sec`, `db_cpu_sec`, `aas`, `db_cpu_pct` |
| I/O | `logical_reads_per_sec`, `physical_reads_per_sec`, `physical_writes_per_sec`, `redo_mb_per_sec` |
| 吞吐 | `executes_per_sec`, `user_calls_per_sec`, `transactions_per_sec` |
| 解析 | `parses_per_sec`, `hard_parses_per_sec`, `hard_parse_pct` |
| 元信息 | `snap_id`, `begin_time`, `end_time`, `interval_sec` |

- `profile` 按 `snap_id` 升序，走势与基线偏离由调用方比对，MCP 不做汇总与判定。
- `transactions_per_sec` = (`user commits` + `user rollbacks`) / 秒。
- 累计量在实例重启后归零，跨越重启点的那一行增量会异常（偏小或为负），叙述前先看 `interval_sec` 与相邻行是否自洽。

---

## 安全与质量约束（全局生效）

1. **鉴权**：所有工具走 `McpClusterDetailPermission`，由 `auth_parse_instances` 将 `address` 映射到实例所属的 `cluster_id`，走 IAM 集群级权限校验。
2. **实例越权防护**：由 `bk_cloud_id` + `address` 定位机器和存储实例，并校验其属于 Oracle 集群，拒绝连接任意实例。
3. **SQL 注入防护**：用户输入在 Python 侧渲染为转义后的 SQL 字面量（仅支持 None/数字/字符串）；拼入 SQL 的标识符（`sql_id` 限字母/数字/下划线、AWR `format` 走枚举白名单、历史 ASH `bucket_minutes` 走取值白名单）均经白名单校验。
4. **结果上限**：列表接口统一受 `ORACLE_MAX_ROWS` 约束；按行返回文本的接口另设独立上限（`ORACLE_XPLAN_MAX_LINES` 2000 行、`ORACLE_AWR_MAX_LINES` 10 万行）；DRS 侧另有 10 万行 / 64MB 上限。
5. **连接方式**：一次工具调用的多条 SQL 合并为一次 DRS 请求，在同一连接上顺序执行；DRS 每次请求独立建连，用完即关。**例外**：历史 ASH 工具用两次 DRS 调用——第一次解析 `snap_id` 区间，第二次带着 `snap_id` 字面量做窗口探测与聚合，以确保底层分区表的裁剪静态生效。
6. **只读**：DRS 只放行 `SELECT` / `WITH`（拒绝 `FOR UPDATE`），连接账号为 DRS 侧配置的只读账号，应仅授予只读权限。
7. **AWR / ASH 开关**：`ORACLE_ENABLE_AWR` 统一控制内存 ASH、历史 ASH 与全部 AWR 工具（同属 Diagnostics Pack）。
