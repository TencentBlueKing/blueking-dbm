# SQLServer MCP 工具集说明

> 来源：`backend/dbm_aiagent/mcp_tools/sqlserver/views.py`
> 命名空间：`sqlserver_query`（所有工具均通过 `name_prefix="sqlserver_query"` 注册）
> 权限：`McpClusterDetailPermission`，按集群粒度鉴权（`auth_parse_clusters`）
> 标签：所有工具均为 `READ` 类（只读，不会写入 DB）
> MCP 分组：`DBMMcpTools.SQLSERVER_QUERY`

## 公共说明

- **`address` 行为约定**：
  - `cluster_topo` / `instance_summary` / `list_databases` / `server_config_summary`：未传时返回 **集群内全部实例** 的结果。
  - 其余“需要落到具体实例上跑 SQL”的工具：未传时 **缺省走 master**。
- **标识符校验**：所有 `dbname / schema / table / table_name` 仅允许 `[A-Za-z_][A-Za-z0-9_$#@]{0,127}`。
- **批量结果约定**（仅适用于索引分析功能域 5 个工具）：每张表独立返回 `status` ∈ `ok / not_found / error`，单表失败不会让整批失败，`results[i]` 顺序与入参 `tables` 一致。
- **per-instance 结果约定**（适用于 `instance_summary / list_databases / server_config_summary`）：每实例独立返回 `error_msg`，空字符串表示成功。

## 工具一览

| # | 工具方法 | 用途 | 默认作用范围 |
|---|---|---|---|
| 1 | `cluster_topo` | 查询集群拓扑结构 | 整个集群 |
| 2 | `instance_summary` | 实例基础信息（版本、Edition、CPU、内存、启动时间） | 集群内全部实例 / 指定实例 |
| 3 | `list_databases` | 实例上的数据库清单（状态、恢复模式、大小） | 集群内全部实例 / 指定实例 |
| 4 | `list_table_status` | 库内用户表状态清单（行数、占用、统计过期度） | 单库，缺省 master |
| 5 | `server_config_summary` | 关键 `sp_configure` 配置项白名单 | 集群内全部实例 / 指定实例 |
| 6 | `blocking_sessions` | 当前阻塞会话快照（被阻塞 + 阻塞源） | 缺省 master |
| 7 | `wait_stats_snapshot` | `dm_os_wait_stats` 累计等待 TOP N（已剔良性等待） | 缺省 master |
| 8 | `top_requests` | 当前活跃请求 TOP N（cpu/duration/reads/writes） | 缺省 master |
| 9 | `explain_sql` | SHOWPLAN_XML 估算执行计划（仅编译不执行） | 缺省 master |
| 10 | `slow_log_query` | 慢日志（`[Monitor].[dbo].[TRACE_TSQL]`） | 缺省 master |
| 11 | `get_table_schema` | 批量查询表结构（列、约束、PK、FK） | 缺省 master |
| 12 | `get_table_indexes` | 批量查询表上现有索引清单 | 缺省 master |
| 13 | `get_table_stats` | 批量查询表统计对象状态（含过期判定） | 缺省 master |
| 14 | `get_index_usage_stats` | 批量查询索引使用画像（seek/scan/lookup/update 累计） | 缺省 master |
| 15 | `get_index_fragmentation` | 批量查询索引碎片状态（LIMITED 模式） | 缺省 master |

---

## 1. `cluster_topo`：查询集群拓扑

**用途**：查询 SQLServer 集群的拓扑结构，含集群类型、容灾级别、同步模式、存储层实例列表。

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_domain` | string | 是 | 集群域名 |

**输出字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `cluster_type` | string | 集群类型（`sqlserver_single` / `sqlserver_ha` 等） |
| `cluster_domain` | string | 集群域名 |
| `region` | string | 地域 |
| `tolerance_level` | int | 容灾级别 |
| `time_zone` | string | 时区 |
| `sync_mode` | string\|null | 数据同步模式，仅 `sqlserver_ha` 有效 |
| `storage[]` | object[] | 存储层实例列表，元素结构见下 |

存储实例 `storage[]` 元素字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `address` | string | `ip:port` |
| `status` / `phase` | string | 实例状态 / 生命周期状态 |
| `machine_type` | string | 机器类型 |
| `bk_idc_id` / `bk_idc_name` | int / string | 机房 |
| `bk_idc_area_id` / `bk_idc_area` | int / string | 机房区域 |
| `bk_sub_zone_id` / `bk_sub_zone` | int / string | 子 Zone |
| `instance_role` | string | 实例角色 |
| `instance_inner_role` | string | 实例内部角色（master / slave） |
| `is_stand_by` | bool | DBHA 切换备选标志 |

---

## 2. `instance_summary`：实例基础信息

**用途**：查询实例的版本、Edition、CPU、内存、启动时间等基础信息。`address` 不传时返回集群内全部实例。

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_domain` | string | 是 | 集群域名 |
| `address` | string | 否 | `ip:port`；不传返回全部实例 |

**输出字段**（顶层）

| 字段 | 说明 |
|---|---|
| `cluster_domain` | 集群域名 |
| `results[]` | 实例信息列表 |

`results[]` 元素：

| 字段 | 类型 | 说明 |
|---|---|---|
| `address` | string | `ip:port` |
| `role` | string | 实例内部角色（master / slave） |
| `is_stand_by` | bool | 是否备份/standby |
| `data` | object\|null | 单实例摘要数据（查询失败时为 null） |
| `error_msg` | string | 单实例错误，空串表示成功 |

`data` 字段：

| 字段 | 说明 |
|---|---|
| `machine_name` | 主机名 |
| `server_name` | 服务名 |
| `instance_name` | 实例名（默认实例为空） |
| `product_version` | 产品版本号，如 `15.0.4188.2` |
| `product_level` | 产品级别（RTM/SP1） |
| `edition` | 版本（Enterprise/Standard） |
| `collation` | 默认排序规则 |
| `is_clustered` | 是否故障转移群集 1/0 |
| `is_hadr_enabled` | 是否启用 AlwaysOn 1/0；2008/2008R2 上为 NULL |
| `is_integrated_security_only` | 是否仅 Windows 身份验证 1/0 |
| `cpu_count` | CPU 逻辑核数 |
| `sqlserver_start_time` | 启动时间（用最早系统会话登录时间近似） |
| `sql_memory_used_mb` | 进程当前已用物理内存（工作集），可能略大于 max（含线程栈/CLR 等） |
| `sql_memory_max_mb` | `max server memory` 配置上限；`2147483647` 表示未限制 |
| `sql_memory_min_mb` | `min server memory` 配置下限 |

---

## 3. `list_databases`：数据库清单

**用途**：列出实例上的数据库清单，含状态、恢复模式、兼容级别、大小。

**输入字段**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `address` | string | 否 | null | 不传查全部实例 |
| `order_by` | enum | 否 | `total_size_mb` | 排序键：`total_size_mb` / `data_size_mb` / `log_size_mb` |
| `order` | enum | 否 | `desc` | 排序方向：`asc` / `desc` |

**输出字段**

| 字段 | 说明 |
|---|---|
| `cluster_domain` | 集群域名 |
| `results[]` | 实例数据库清单列表 |

`results[]` 元素：

| 字段 | 说明 |
|---|---|
| `address` | `ip:port` |
| `role` | 实例内部角色 |
| `is_stand_by` | 是否 standby 角色 |
| `databases[]` | 数据库行列表 |
| `database_count` | 数据库数量 |
| `error_msg` | 错误信息，空串表示成功 |

`databases[]` 元素：

| 字段 | 说明 |
|---|---|
| `database_id` | 数据库 ID |
| `database_name` | 数据库名 |
| `state` | `ONLINE` / `OFFLINE` / `RESTORING` 等 |
| `recovery_model` | `FULL` / `SIMPLE` / `BULK_LOGGED` |
| `compatibility_level` | 兼容级别 |
| `collation` | 排序规则 |
| `create_date` | 创建时间 |
| `is_read_only` | 是否只读 1/0 |
| `data_size_mb` | 数据文件大小 MB |
| `log_size_mb` | 日志文件大小 MB |

---

## 4. `list_table_status`：库内用户表状态清单

**用途**：列出业务库下用户表的状态信息（行数、占用大小、最近活跃、统计过期度）。**这是“做精细分析（`get_table_schema` / `get_table_indexes` 等）之前先定位值得分析的表”的入口工具。** 兼容 SQL Server 2008 ~ 2022。

**输入字段**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `dbname` | string | 是 | - | 业务库名 |
| `schema` | string | 否 | null | schema 过滤；不传返回所有 schema |
| `table_name` | string | 否 | null | 表名精确过滤，传入后等价『查这一张表的状态』，`limit` 自动收敛为 1，表不存在返回空列表 |
| `address` | string | 否 | null | 不传缺省走 master |
| `limit` | int | 否 | 200 | 返回前 N 条；最大 1000 |
| `verbose` | enum | 否 | `summary` | `summary` / `detail` / `count_only` 三态枚举（互斥） |
| `order_by` | enum | 否 | `total_size_mb` | 见下方说明 |
| `order` | enum | 否 | `desc` | `desc` / `asc` |

**`verbose` 三态语义**：
- `summary`（默认）：仅返回 4 个核心字段（`schema_name` / `table_name` / `row_count` / `total_size_mb`），token 友好。
- `detail`：返回全部 20 个字段，索引分析等深度场景使用。
- `count_only`：跳过明细查询，仅返回 `total_user_table_count`（叠加 `schema/table_name` 过滤后），`tables=[]`、`limit=0`；用于回答“这个库一共有多少张用户表”。**此模式下 `order_by/order` 静默忽略**。

**`order_by` 选项**：
- `total_size_mb`：找大表（最常见入口）
- `row_count`：按行数
- `index_size_mb`：找索引膨胀的表
- `stats_outdated_count`：找统计过期最严重的表（`UPDATE STATISTICS` 候选）
- `last_user_update`：按写入活跃度排序，`desc=最近被写`，`asc=最久未被写`

> 注意：`summary` 模式只返回 4 个 L1 字段，若按非 L1 字段排序，明细里看不到该字段值，需要查看请用 `verbose=detail`。

**输出字段**（顶层）

| 字段 | 说明 |
|---|---|
| `cluster_domain` | 集群域名 |
| `address` / `role` | 实际查询的实例地址 / 角色 |
| `dbname` | 目标业务库名 |
| `schema_filter` / `table_filter` | 过滤值回显，空表示未过滤 |
| `limit` | 实际生效的 limit；`count_only` 时为 0 |
| `table_count` | 本次返回的明细条数；`count_only` 时为 0 |
| `verbose` | 实际生效的输出粒度 |
| `total_user_table_count` | 当前库（叠加过滤后）用户表总数；仅 `count_only` 时填值，否则为 null |
| `order_by` / `order` | 实际生效的排序键/方向；`count_only` 时为 null |
| `tables[]` | 表状态清单 |

`tables[]` 元素（按 verbose 决定）：

L1（`summary` / `detail` 都有）：`schema_name` / `table_name` / `row_count` / `total_size_mb`。

L2~L4（仅 `detail`）：

| 字段 | 说明 |
|---|---|
| `object_id` | 表对象 ID |
| `create_date` / `modify_date` | 创建时间 / 最近一次 DDL 时间 |
| `is_heap` | 是否堆表（无聚集索引） |
| `index_count` | 非堆索引数（聚集 + 非聚集） |
| `partition_count` | 分区数；非分区为 1 |
| `has_primary_key` | 是否有主键 |
| `data_size_mb` | 数据空间 MB（含 LOB / row-overflow） |
| `index_size_mb` | 非聚集索引空间 MB |
| `last_user_seek/scan/lookup/update` | 索引最近一次 seek/scan/lookup/update 时间 |
| `total_modification_counter` | 该表所有索引/统计累计未消化修改次数总和（`sys.sysindexes.rowmodctr`） |
| `stats_outdated_count` | 该表上“统计画像可能过期”的统计对象数量；`>0` 时建议优先 `UPDATE STATISTICS`（轻量、不阻塞），而不是 `ALTER INDEX REBUILD`（后者请结合 `get_index_fragmentation` 的碎片率独立判断） |

---

## 5. `server_config_summary`：实例关键配置摘要

**用途**：返回白名单内的 `sp_configure` 配置项。

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_domain` | string | 是 | 集群域名 |
| `address` | string | 否 | 不传查全部实例 |

**输出字段**

`results[]` 元素：

| 字段 | 说明 |
|---|---|
| `address` / `role` / `is_stand_by` | 实例位置信息 |
| `configurations[]` | 配置项列表 |
| `error_msg` | 错误信息，空串表示成功 |

`configurations[]` 元素：

| 字段 | 说明 |
|---|---|
| `name` | 配置项名称，例如 `max server memory (MB)` |
| `value` | 配置值（已设置但可能未生效） |
| `value_in_use` | 当前生效值 |
| `minimum` / `maximum` | 允许最小/最大值 |
| `is_dynamic` | 是否无需重启即可生效 1/0 |
| `is_advanced` | 是否高级选项 1/0 |
| `description` | 配置项描述 |

---

## 6. `blocking_sessions`：当前阻塞会话快照

**用途**：返回当前被阻塞的请求 + 阻塞源信息（按等待时间倒序）。

**输入字段**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `address` | string | 否 | null | 不传缺省走 master |
| `top` | int | 否 | 20 | 取值 (0, 200] |

**输出字段**

| 字段 | 说明 |
|---|---|
| `cluster_domain` / `address` / `role` | 实例位置 |
| `blocking_count` | 阻塞链条数 |
| `blocking_sessions[]` | 阻塞会话列表 |

`blocking_sessions[]` 元素：

| 字段 | 说明 |
|---|---|
| `session_id` / `blocking_session_id` | 被阻塞会话 ID / 阻塞源会话 ID |
| `status` / `command` | 请求状态 / 命令类型 |
| `wait_type` / `wait_time_ms` / `wait_resource` | 等待类型 / 当前等待时长 / 等待资源描述 |
| `cpu_time_ms` / `elapsed_time_ms` | CPU 时间 / 总耗时 |
| `reads` / `writes` / `logical_reads` | 物理读 / 物理写 / 逻辑读 |
| `database_name` / `login_name` / `host_name` / `program_name` | 被阻塞会话所在 DB / 登录名 / 客户端主机 / 客户端程序 |
| `blocker_login_name` / `blocker_host_name` / `blocker_program_name` | 阻塞源登录名 / 主机 / 程序 |
| `sql_text` / `sql_text_truncated` | SQL 文本（已截断）/ 是否截断 1/0 |

---

## 7. `wait_stats_snapshot`：累计等待统计 TOP N

**用途**：基于 `sys.dm_os_wait_stats` 的累计等待统计 TOP N，**已剔除良性等待**。

**输入字段**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `address` | string | 否 | null | 不传缺省走 master |
| `top` | int | 否 | 15 | 取值 (0, 100] |

**输出字段**

| 字段 | 说明 |
|---|---|
| `cluster_domain` / `address` / `role` | 实例位置 |
| `wait_stats[]` | 等待事件 TOP N |

`wait_stats[]` 元素：

| 字段 | 说明 |
|---|---|
| `wait_type` | 等待类型 |
| `waiting_tasks_count` | 发生等待的任务数 |
| `wait_time_ms` | 累计等待时长 |
| `max_wait_time_ms` | 单次最长等待时长 |
| `signal_wait_time_ms` | 信号等待时长（反映 CPU 调度压力） |
| `resource_wait_time_ms` | 资源等待时长（= `wait_time_ms - signal_wait_time_ms`） |
| `avg_wait_time_ms` | 平均单次等待时长 |

---

## 8. `top_requests`：当前活跃请求 TOP N

**用途**：列出当前活跃请求 TOP N，按 cpu/duration/reads/writes 排序。

**输入字段**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `address` | string | 否 | null | 不传缺省走 master |
| `top` | int | 否 | 20 | 取值 (0, 100] |
| `order_by` | enum | 否 | `cpu` | `cpu` / `duration` / `reads` / `writes` |

**输出字段**

| 字段 | 说明 |
|---|---|
| `cluster_domain` / `address` / `role` | 实例位置 |
| `order_by` | 实际生效的排序维度 |
| `top_requests[]` | 活跃请求列表 |

`top_requests[]` 元素：

| 字段 | 说明 |
|---|---|
| `session_id` | 会话 ID |
| `status` / `command` | 请求状态 / 命令类型 |
| `blocking_session_id` | 阻塞源会话 ID，0 表示无阻塞 |
| `wait_type` / `wait_time_ms` | 等待类型 / 当前等待时长 |
| `cpu_time_ms` / `elapsed_time_ms` | CPU 时间 / 总耗时 |
| `reads` / `writes` / `logical_reads` | 物理读 / 物理写 / 逻辑读 |
| `row_count` | 已返回行数 |
| `database_name` / `login_name` / `host_name` / `program_name` | DB / 登录名 / 客户端主机 / 客户端程序 |
| `sql_text` / `sql_text_truncated` | SQL 文本（已截断） / 是否截断 1/0 |

---

## 9. `explain_sql`：估算执行计划

**用途**：返回 `SHOWPLAN_XML` 估算执行计划（**仅编译不执行**，不会真正读写数据）。

**安全限制**：
- 仅允许 `SELECT` / `WITH(CTE)` 语句；
- 不允许多语句、写操作、DDL、`xp_/sp_` 调用、`WAITFOR`、`USE/GO` 等。

**输入字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `cluster_domain` | string | 是 | 集群域名 |
| `dbname` | string | 是 | 目标库名 |
| `query_sql` | string | 是 | 待分析 SQL |
| `address` | string | 否 | 不传缺省走 master |

**输出字段**

| 字段 | 说明 |
|---|---|
| `cluster_domain` / `address` / `role` / `dbname` | 实例位置 + 目标库 |
| `explain_xml` | `SHOWPLAN_XML` 返回的估算计划 XML |
| `rewritten` | 用户提交的 SQL 是否被改写；当前阶段始终为 `false` |
| `is_trivial` | 是否为无真实查询计划的平凡语句（如 `SELECT 1`）；为 true 时无需深度分析 |

---

## 10. `slow_log_query`：慢日志查询

**用途**：查询慢日志，来源 `[Monitor].[dbo].[TRACE_TSQL]`。

**输入字段**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `address` | string | 否 | null | 不传缺省走 master |
| `start_time` | datetime | 否 | end_time-1h | 起始时间（含），ISO 格式 |
| `end_time` | datetime | 否 | now | 结束时间（含），ISO 格式 |
| `database_name` | string | 否 | null | 业务库名，精确匹配 `TRACE_TSQL.DATABASENAME` |
| `min_duration_ms` | int | 否 | 0 | 最小耗时阈值（毫秒） |
| `top` | int | 否 | 20 | 取值 (0, 200] |
| `order_by` | enum | 否 | `duration` | `duration` / `cpu` / `reads` / `writes` / `starttime` |

**输出字段**

| 字段 | 说明 |
|---|---|
| `cluster_domain` / `address` / `role` | 实例位置 |
| `filter` | 实际生效的过滤条件回显（`start_time` / `end_time` / `database_name` / `min_duration_ms` / `order_by`） |
| `row_count` | 返回的慢日志条数 |
| `slow_logs[]` | 慢日志列表 |

`slow_logs[]` 元素：

| 字段 | 说明 |
|---|---|
| `starttime` / `endtime` | SQL 起止时间 |
| `duration_ms` | 总耗时（毫秒，由 DURATION 微秒换算） |
| `cpu_ms` | CPU 时间（毫秒） |
| `reads` / `writes` / `row_counts` | 逻辑读次数 / 写次数 / 返回行数 |
| `database_name` / `login_name` / `nt_user_name` / `application_name` / `object_name` | 库名 / 登录名 / NT 用户 / 客户端 / 对象名 |
| `error` | 错误码，0 表示无错误 |
| `sql_text` / `sql_text_truncated` | SQL 文本（已截断）/ 是否截断 1/0 |

---

## 索引分析功能域（共 5 个工具）

> P0：`get_table_schema` / `get_table_indexes` / `get_table_stats`
> P1：`get_index_usage_stats` / `get_index_fragmentation`

### 公共输入字段

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `dbname` | string | 是 | - | 目标库名 |
| `tables` | string[] | 是 | - | 1~20 张表，整批共用同一个 schema；重复项去重并保持首次出现顺序 |
| `schema` | string | 否 | `dbo` | 表所在 schema |
| `address` | string | 否 | null | 不传缺省走 master |

### 公共输出顶层字段

| 字段 | 说明 |
|---|---|
| `cluster_domain` / `address` / `role` / `dbname` / `schema` | 实例位置 + 目标库 + schema |
| `table_count` | 入参表数量（去重后） |
| `ok_count` | `status=ok` 的表数量 |
| `results[]` | 每张表结果，顺序与入参 `tables` 一致 |

### `results[]` 公共字段

| 字段 | 说明 |
|---|---|
| `table` | 表名 |
| `status` | `ok` / `not_found` / `error` |
| `error` | 非 ok 时的错误说明；ok 时为 null |

> 业务字段由各工具子类追加，见下文。

---

### 11. `get_table_schema`：批量查询表结构

**用途**：返回列、类型、可空、计算列、默认/检查约束、主键、外键。

`results[i]` 业务字段：

| 字段 | 说明 |
|---|---|
| `columns[]` | 列清单 |
| `primary_key` | 主键信息；无主键时为 null |
| `foreign_keys[]` | 外键清单 |

`columns[]` 元素：

| 字段 | 说明 |
|---|---|
| `column_id` / `column_name` | 列 ID / 列名 |
| `type_name` / `type_display` | 类型名（不含长度） / 拼好长度精度的展示，例如 `NVARCHAR(50)` |
| `max_length` | 最大长度（字节，varchar=-1 表示 MAX） |
| `precision` / `scale` | 精度 / 小数位数 |
| `is_nullable` | 是否可空 1/0 |
| `is_identity` | 是否 IDENTITY 1/0 |
| `is_computed` / `is_persisted` / `computed_definition` | 是否计算列 / 是否持久化 / 表达式 |
| `is_rowguidcol` / `is_rowversion` | 是否 ROWGUIDCOL / 是否 rowversion/timestamp 1/0 |
| `default_definition` | 默认值约束表达式 |
| `collation` | 排序规则 |

`primary_key` 字段：

| 字段 | 说明 |
|---|---|
| `name` | 主键约束名 |
| `type` | 索引类型描述（如 `CLUSTERED`） |
| `columns[]` | 主键列（按 `key_ordinal`） |

`foreign_keys[]` 元素：

| 字段 | 说明 |
|---|---|
| `name` | 外键名 |
| `referenced_schema` / `referenced_table` | 被引用表所在 schema / 表名 |
| `on_delete` / `on_update` | 联动行为 |
| `is_disabled` / `is_not_trusted` | 是否禁用 / 未经信任 1/0 |
| `columns[]` / `referenced_columns[]` | 本表 / 被引用表参与外键的列（按列序） |

---

### 12. `get_table_indexes`：批量查询表索引清单

**用途**：返回表上现有索引清单（含键列、INCLUDE 列、唯一性、是否禁用、近似行数、压缩状态）。

`results[i]` 业务字段：

| 字段 | 说明 |
|---|---|
| `indexes[]` | 索引清单 |
| `index_count` | 索引数量；非 ok 时为 0 |

`indexes[]` 元素：

| 字段 | 说明 |
|---|---|
| `index_id` / `index_name` | 索引 ID / 名 |
| `type_id` / `type_desc` | 索引类型 |
| `is_unique` / `is_primary_key` / `is_unique_constraint` / `is_disabled` | 唯一性 / 主键 / 唯一约束 / 是否禁用 1/0 |
| `has_filter` / `filter_definition` | 是否过滤索引 / 过滤条件 |
| `fill_factor` / `is_padded` | 填充因子 / 是否填充 |
| `approx_rows` | 索引第一个分区的近似行数 |
| `data_compression` | 压缩状态 `NONE` / `ROW` / `PAGE` / `COLUMNSTORE` |
| `key_columns[]` | 键列（`name` / `ordinal` / `is_descending`） |
| `included_columns[]` | INCLUDE 列（`name`） |

---

### 13. `get_table_stats`：批量查询表统计对象状态

**用途**：返回统计对象的最近更新时间、采样行数、修改行数、是否过期。**用于诊断执行计划行数估算偏差是否由统计过期引起**。

`results[i]` 业务字段：

| 字段 | 说明 |
|---|---|
| `stats[]` | 统计对象清单 |
| `stats_count` | 统计对象数量；非 ok 时为 0 |
| `outdated_count` | 被判定为过期的统计对象数量；非 ok 时为 0 |

`stats[]` 元素：

| 字段 | 说明 |
|---|---|
| `stats_id` / `stats_name` | 统计对象 ID / 名 |
| `columns[]` | 涉及的列（按 `stats_column_id`） |
| `auto_created` / `user_created` | 是否系统自动创建 / 用户显式创建 1/0 |
| `no_recompute` | 是否禁止自动更新 1/0 |
| `has_filter` / `filter_definition` | 是否过滤统计 / 条件 |
| `last_updated` | 最近更新时间 |
| `rows` / `rows_sampled` / `unfiltered_rows` | 总行数 / 实际采样行数 / 过滤前行数 |
| `modification_counter` | 自上次统计更新以来表的修改次数 |
| `steps` | 直方图步数 |
| `bound_to_index` / `bound_index_type` | 是否随某索引自动维护 / 绑定索引的类型 |
| `is_outdated` | 基于经验阈值的过期判定结果 |

---

### 14. `get_index_usage_stats`：批量查询索引使用画像

**用途**：返回每个索引的 user_seek/scan/lookup/update 累计计数。**计数为实例启动以来累计**，故同时返回 `sqlserver_start_time` 作为样本起点。**用于识别冗余索引或从未使用的索引**。

输出顶层除公共字段外，多一个：

| 字段 | 说明 |
|---|---|
| `sqlserver_start_time` | 实例启动时间（累计计数样本起点；全实例共享，故置于顶层） |

`results[i]` 业务字段：

| 字段 | 说明 |
|---|---|
| `indexes[]` | 索引使用画像清单 |
| `index_count` | 索引数量；非 ok 时为 0 |

`indexes[]` 元素：

| 字段 | 说明 |
|---|---|
| `index_id` / `index_name` / `type_desc` | 索引 ID / 名 / 类型描述 |
| `is_unique` / `is_primary_key` | 唯一性 / 主键 1/0 |
| `user_seeks` / `user_scans` / `user_lookups` / `user_updates` | seek/scan/lookup/索引维护引发的更新 累计次数 |
| `last_user_seek` / `last_user_scan` / `last_user_lookup` / `last_user_update` | 最近一次时间 |

---

### 15. `get_index_fragmentation`：批量查询索引碎片状态

**用途**：基于 `sys.dm_db_index_physical_stats` 的 LIMITED 模式扫描。**默认仅返回 `page_count >= 1000` 的索引**（小索引碎片对性能基本无影响）。**用于辅助决策 `REORGANIZE` / `REBUILD`**。

**专属输入字段**（在公共输入基础上追加）

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `min_page_count` | int | 否 | 1000 | 仅返回 `page_count >=` 该阈值的索引；0 表示不过滤 |

**专属输出顶层字段**（在公共输出基础上追加）

| 字段 | 说明 |
|---|---|
| `scan_mode` | 扫描模式（固定 `LIMITED`） |
| `min_page_count` | 过滤的最小页数阈值回显 |

`results[i]` 业务字段：

| 字段 | 说明 |
|---|---|
| `indexes[]` | 各索引碎片信息 |
| `row_count` | 返回行数；非 ok 时为 0 |

`indexes[]` 元素：

| 字段 | 说明 |
|---|---|
| `index_id` / `index_name` / `index_type_desc` | 索引 ID / 名 / 类型描述 |
| `alloc_unit_type` | 分配单元类型（`IN_ROW_DATA` / `LOB_DATA`） |
| `partition_number` | 分区号 |
| `avg_fragmentation_pct` | 平均碎片率（%） |
| `fragment_count` | 碎片数量 |
| `avg_fragment_size_pages` | 平均碎片大小（页） |
| `page_count` | 页数（决定是否值得维护） |
| `record_count` | 记录数 |

---

## 典型使用流程示例

### 场景 A：定位“某个库里值得分析的表”
```
list_databases → list_table_status(verbose=summary, order_by=total_size_mb)
              → list_table_status(verbose=detail, order_by=stats_outdated_count)
```

### 场景 B：分析某张表的执行计划是否合理
```
get_table_schema(tables=[T])
get_table_indexes(tables=[T])
get_table_stats(tables=[T])         # 排查统计是否过期
explain_sql(query_sql=...)          # 估算计划
```

### 场景 C：识别冗余索引 + 决定是否 REBUILD
```
get_index_usage_stats(tables=[T])   # seek=0/scan=0 的索引可能是冗余
get_index_fragmentation(tables=[T]) # 碎片率高 + page_count 大 → 考虑 REBUILD
```

### 场景 D：实例侧性能问题排查
```
top_requests(order_by=cpu)          # 找当前 CPU 杀手
blocking_sessions                   # 是否存在阻塞链
wait_stats_snapshot                 # 累计等待画像
slow_log_query                      # 历史慢查询
```