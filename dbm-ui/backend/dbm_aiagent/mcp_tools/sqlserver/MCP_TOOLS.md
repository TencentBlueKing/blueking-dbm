# SQLServer MCP 工具集说明

> 来源：`backend/dbm_aiagent/mcp_tools/sqlserver/views.py`
> 命名空间：`sqlserver_query`（所有工具均通过 `name_prefix="sqlserver_query"` 注册）
> 权限：`McpClusterDetailPermission`，按集群粒度鉴权（`auth_parse_clusters`）
> 标签：所有工具均为 `READ` 类（只读，不会写入 DB）
> MCP 分组：`DBMMcpTools.SQLSERVER_QUERY`

## 公共说明

- **`address` 行为约定**：
  - `cluster_topo` / `instance_summary` / `list_databases` / `server_config_summary`：未传时返回 **集群内全部实例** 的结果。
  - 其余“需要落到具体实例上跑 SQL”的工具（包括 `database_file_usage` / `get_stored_procedure` 等）：未传时 **缺省走 master**。
- **标识符校验**：所有 `dbname / schema / table / table_name` 仅允许 `[A-Za-z_][A-Za-z0-9_$#@]{0,127}`。
- **批量结果约定**（仅适用于索引分析功能域 5 个工具 + `database_file_usage`）：每个目标对象（表 / 数据库）独立返回 `status` ∈ `ok / not_found / error`，单项失败不会让整批失败，`results[i]` 顺序与入参一致。
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
| 16 | `sync_status` | 分析集群数据同步状态（自动识别 Mirroring / AlwaysOn，含滞后队列、commit_lag、健康摘要）；支持 `databases` 白名单过滤 | 整个集群 |
| 17 | `database_file_usage` | 批量查询数据库 MDF/LDF 文件容量使用率（已用/已分配 + 文件级明细 + 库级汇总） | 缺省 master |
| 18 | `get_stored_procedure` | 按精确坐标获取单个 SP 的完整原始 T-SQL 定义体，专用于静态风险/安全分析 | 缺省 master |

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

## 16. `sync_status`：集群数据同步状态分析（Mirroring / AlwaysOn）

**用途**：分析 SQLServer 集群的数据同步状态。**后端根据 `SqlserverClusterSyncMode` 自动识别集群是 `mirroring` 还是 `always_on`**，调用方无须感知差异；统一输出 schema，差异通过 `mirroring` / `always_on` 两个字段（互斥）承载。**核心价值**：一次调用即可让 LLM 拿到「健康摘要 + 滞后队列 + 估算追齐秒数 + 具体 issue 列表」，可直接给出诊断结论。

**通道**：`sqlserver_sys_read_rpc`，仅访问 `sys.*` DMV，**无须业务库权限**。集群内所有实例并发采集，单实例失败不影响整体。

**输入字段**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `databases` | string[] | 否 | `[]` | DB 名白名单（不区分大小写）；不传或传空数组 = 全量返回；用于在大集群下让 LLM 集中分析特定库的同步情况，缩小上下文 |

**输出顶层字段**

| 字段 | 说明 |
|---|---|
| `cluster_domain` | 集群域名 |
| `cluster_type` | 集群类型（`sqlserver_ha` / `sqlserver_single`） |
| `sync_mode` | `mirroring` / `always_on`；单节点集群为 null |
| `summary` | 整体同步健康摘要（LLM 第一眼读这里） |
| `mirroring` | mirroring 详细数据；非 mirroring 集群为 null |
| `always_on` | AlwaysOn 详细数据；非 AG 集群为 null |
| `results[]` | 各实例采集结果（含 error_msg） |
| `filter` | 用户传入 `databases` 白名单时回显的过滤情况：含 `requested`（原始请求名单去重后小写）、`matched`（集群中实际命中的库名）、`missing`（未在集群中找到的库名）；未指定 `databases` 入参时为 null |

### `summary` 字段（通用）

| 字段 | 说明 |
|---|---|
| `overall_health` | `HEALTHY` / `PARTIALLY_HEALTHY` / `NOT_HEALTHY` / `N/A` |
| `node_count` | AG 副本数；mirroring 不适用，固定 null |
| `database_count` | 参与同步的数据库（视角行）总数 |
| `unhealthy_database_count` | 不健康数据库（视角行）数量 |
| `max_log_send_queue_mb` | 全集群最大 log_send_queue（MB）。阈值：>=100 警告 / >=1024 严重 |
| `max_redo_queue_mb` | 全集群最大 redo_queue（MB），阈值同上 |
| `max_commit_lag_seconds` | AG 专属：primary/secondary 上 `last_commit_time` 差最大值（秒）。阈值：>=5 警告 / >=60 严重 |
| `issues[]` | 顶层问题列表（聚合各 DB 的关键 issue） |
| `reason` | `overall_health=N/A` 时的原因说明 |

### `mirroring.databases[]`（每个被镜像 DB 一行）

| 字段 | 说明 |
|---|---|
| `database_name` | 数据库名 |
| `principal_address` / `mirror_address` | 看到该 DB 为 PRINCIPAL / MIRROR 的实例 `ip:port` |
| `mirroring_role_desc` | `PRINCIPAL` / `MIRROR` |
| `mirroring_state_desc` | `SYNCHRONIZED` / `SYNCHRONIZING` / `SUSPENDED` / `DISCONNECTED` / `PENDING_FAILOVER` |
| `mirroring_safety_level_desc` | `FULL`（同步模式）/ `OFF`（异步模式） |
| `mirroring_partner_name` / `mirroring_partner_instance` | 对端 endpoint / 实例 |
| `mirroring_witness_name` / `mirroring_witness_state_desc` | 见证服务器及其状态 |
| `mirroring_failover_lsn` / `mirroring_end_of_log_lsn` / `mirroring_replication_lsn` | 关键 LSN |
| `mirroring_connection_timeout` / `mirroring_redo_queue_type` / `mirroring_redo_queue` | 连接超时 / redo 限速配置 |
| `log_send_queue_mb` | 主端待发送日志（MB）；阈值 >=100 警告 / >=1024 严重 |
| `redo_queue_mb` | 备端待重做日志（MB），阈值同上 |
| `log_send_rate_kbps` / `redo_rate_kbps` | 当前发送 / redo 速率 |
| `transaction_delay_ms` | 同步模式下事务等待 ack 的延迟（毫秒） |
| `log_send_flow_control_ms_per_sec` | 主端被流控阻塞时长 ms/s |
| `mirrored_write_tps` | 镜像写事务速率 |
| `estimated_send_seconds` | 估算清空 log_send_queue 所需秒数（速率为 0 时为 null） |
| `estimated_redo_seconds` | 估算清空 redo_queue 所需秒数 |
| `is_healthy` | 综合判定：SYNCHRONIZED 且队列 < 警告阈值 |
| `issues[]` | 该 DB 的具体 issue（如 `state=SUSPENDED`、`log_send_queue=200MB(warn)`） |

### `always_on.availability_groups[]`（每个 AG 一项）

**AG 级**：

| 字段 | 说明 |
|---|---|
| `ag_name` / `group_id` | AG 名 / GUID |
| `primary_replica` | 当前 primary 副本实例名 |
| `automated_backup_preference_desc` | 自动备份偏好 |
| `failure_condition_level` / `health_check_timeout` | 故障检测灵敏度 |
| `primary_recovery_health_desc` / `secondary_recovery_health_desc` | 副本恢复健康 |
| `synchronization_health_desc` | `HEALTHY` / `PARTIALLY_HEALTHY` / `NOT_HEALTHY` |
| `replicas[]` | 副本列表（primary 在前） |
| `listeners[]` | Listener 列表（VIP/Port/状态） |
| `cluster_members[]` | WSFC 仲裁节点列表（用于判断仲裁健康） |

**`replicas[]` 元素**：

| 字段 | 说明 |
|---|---|
| `replica_id` / `replica_server_name` / `endpoint_url` | 副本标识 |
| `role_desc` | `PRIMARY` / `SECONDARY` / `RESOLVING` |
| `availability_mode_desc` | `SYNCHRONOUS_COMMIT` / `ASYNCHRONOUS_COMMIT` |
| `failover_mode_desc` | `AUTOMATIC` / `MANUAL`（仅同步副本可 AUTOMATIC） |
| `session_timeout` / `backup_priority` | 会话超时秒 / 备份优先级 |
| `primary_role_allow_connections_desc` / `secondary_role_allow_connections_desc` | 各角色允许的连接（只读路由配置） |
| `seeding_mode_desc` | `AUTOMATIC` / `MANUAL` |
| `operational_state_desc` / `connected_state_desc` / `recovery_health_desc` | 运行 / 连接 / 恢复健康状态 |
| `synchronization_health_desc` | 副本级同步健康 |
| `join_state_desc` / `is_failover_ready` | WSFC 加入状态 / 是否可切换 |
| `databases[]` | 该副本上各 DB 的同步状态 |

**`replicas[].databases[]` 元素**：

| 字段 | 说明 |
|---|---|
| `database_name` / `replica_server_name` | 数据库 / 所在副本 |
| `is_local` / `is_primary_replica` | 是否本地 / 是否 primary |
| `synchronization_state_desc` | `SYNCHRONIZED`（仅同步副本会到达）/ `SYNCHRONIZING`（异步常态）/ `NOT_SYNCHRONIZING`（异常）/ `REVERTING` / `INITIALIZING` |
| `synchronization_health_desc` | `HEALTHY` / `PARTIALLY_HEALTHY` / `NOT_HEALTHY` |
| `database_state_desc` | `ONLINE` / `RESTORING` / `RECOVERING` / `SUSPECT` / `OFFLINE` |
| `suspend_reason_desc` / `is_suspended` | 挂起原因 / 是否挂起 |
| `is_commit_participant` | 是否参与同步提交（仅同步副本为 true） |
| `log_send_queue_mb` / `redo_queue_mb` | 主端待发 / 备端待重做（MB） |
| `log_send_rate_kbps` / `redo_rate_kbps` | 速率 KB/s |
| `last_hardened_lsn` / `last_redone_lsn` / `end_of_log_lsn` / `recovery_lsn` | 关键 LSN |
| `last_hardened_time` / `last_redone_time` / `last_commit_time` / `last_received_time` / `last_sent_time` | 关键时间戳 |
| `estimated_send_seconds` / `estimated_redo_seconds` | 估算追齐秒数（速率为 0 时为 null） |
| `is_failover_ready` / `is_database_joined` | 故障转移就绪 / 已加入 AG |
| `is_healthy` | 综合判定（同步状态 + 未挂起 + 队列 < 警告阈值） |
| `issues[]` | 该 DB 的具体 issue |

**`listeners[]` 元素**：`listener_id` / `dns_name` / `port` / `ip_address` / `ip_subnet_mask` / `is_dhcp` / `state_desc`（`ONLINE` / `OFFLINE` / `ONLINE_PENDING` / `FAILED`）。

**`cluster_members[]` 元素**：`member_name` / `member_type_desc`（`NODE` / `DISK_WITNESS` / …）/ `member_state_desc`（`UP` / `DOWN`）/ `number_of_quorum_votes`。

### `results[]`（per-instance 采集结果）

| 字段 | 说明 |
|---|---|
| `address` / `role` / `is_stand_by` | 实例位置信息 |
| `error_msg` | 该实例采集错误信息；空串表示成功 |

---

## 17. `database_file_usage`：批量查询数据库文件容量使用率

**用途**：批量查询 SQLServer 数据库文件（MDF/NDF/LDF）的容量使用率（已用 / 已分配 / 增长策略），同时返回库级汇总（`data_used_pct` / `log_used_pct`）。**用于在容量告警 / 扩容决策 / 日志增长排查场景下，一次拿到一组库的文件级 + 库级画像**。

**通道**：业务库只读账号；每个库独立 `USE` + 查 `sys.database_files`，单库 OFFLINE / RESTORING / 不存在不会让整批失败。

**输入字段**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `databases` | string[] | 是 | - | 目标数据库名列表，1~20 个；列表内重复项会被去重并保持首次出现的顺序；元素仅允许 `[A-Za-z_][A-Za-z0-9_$#@]{0,127}` |
| `address` | string | 否 | null | 实例地址 `ip:port`；不传缺省走 master |

**输出顶层字段**

| 字段 | 说明 |
|---|---|
| `cluster_domain` | 集群域名 |
| `address` / `role` | 实际查询的实例地址 / 角色 |
| `database_count` | 入参数据库数量（去重后） |
| `ok_count` | `status=ok` 的数据库数量 |
| `results[]` | 每个数据库的文件使用率结果，顺序与入参 `databases` 一致 |

**`results[]` 元素**

| 字段 | 说明 |
|---|---|
| `database` | 数据库名 |
| `status` | `ok` / `error`（库 OFFLINE / RESTORING / 不存在等） |
| `error` | `status` 非 ok 时的错误说明；ok 时为 null |
| `files[]` | 文件级使用率明细（含 mdf/ndf/ldf）；`status` 非 ok 时为空数组 |
| `data_allocated_mb` | 数据文件总分配空间 MB（所有 ROWS 文件加总） |
| `data_used_mb` | 数据文件总已用空间 MB |
| `data_used_pct` | 数据文件整体使用率%（已用/已分配 × 100） |
| `log_allocated_mb` | 日志文件总分配空间 MB（所有 LOG 文件加总） |
| `log_used_mb` | 日志文件总已用空间 MB |
| `log_used_pct` | 日志文件整体使用率%（已用/已分配 × 100） |

**`files[]` 元素**

| 字段 | 说明 |
|---|---|
| `file_id` | 文件 ID |
| `file_name` | 逻辑文件名 |
| `file_type` | 文件类型，0=数据文件(mdf/ndf) 1=日志文件(ldf) |
| `file_type_desc` | 文件类型描述：`ROWS` / `LOG` |
| `physical_name` | 物理文件路径 |
| `allocated_mb` | 已分配空间 MB |
| `used_mb` | 已使用空间 MB |
| `used_pct` | 单文件使用率百分比，例如 85.32 表示 85.32% |
| `max_size_mb` | 文件最大大小 MB；`-1` 表示无限增长 |
| `growth_desc` | 增长策略描述，例如 `64MB` / `10%` / `NONE` |

---

## 18. `get_stored_procedure`：获取单个存储过程的原始 T-SQL 定义体

**用途**：按精确坐标（`cluster_domain` + `dbname` + `schema.proc`）获取 SQLServer 单个存储过程的【完整原始 T-SQL 定义体】，**专用于 LLM 静态风险 / 安全分析**（硬编码凭据、动态 SQL 注入、权限提升、超大 SP、祖传代码识别等）。

**调用约束**：
- 调用方必须**已确切知道 SP 名称**——本工具**不提供枚举 / 模糊匹配 / 批量**。
- 用户未提供 SP 名时，请先反问而不是猜测。
- 如需分析多个 SP，请**多次调用**本工具。
- `procedure` 支持两种形式：`schema.proc`（显式 schema）或 `proc`（缺省 `schema=dbo`）。

**数据源**：`sys.procedures` + `sys.sql_modules.definition`，与 SSMS 右键 Modify 一致；**不做任何脱敏**。

**⚠ 安全提示**：`definition` 字段是原文，可能包含**硬编码密码 / 密钥 / IP**，仅用于分析、**不要原样回显给最终用户**。

**输入字段**

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `cluster_domain` | string | 是 | - | 集群域名 |
| `dbname` | string | 是 | - | 业务库名（实际承载该 SP 的数据库） |
| `procedure` | string | 是 | - | SP 名称：`schema.proc` 或 `proc`（缺省 `schema=dbo`） |
| `max_definition_chars` | int | 否 | 200000 | definition 字符数硬上限；超出则 `status=too_large` 且 `definition=null`（**不截断**，避免风险分析失真）。范围 [10000, 500000] |
| `address` | string | 否 | null | 实例地址 `ip:port`；不传缺省走 master |

**输出字段**（**扁平结构**，一次只查 1 个 SP，不再嵌套 `results[]`）

| 字段 | 说明 |
|---|---|
| `cluster_domain` | 集群域名 |
| `address` / `role` | 实际命中的实例 `ip:port` / 实例角色 |
| `dbname` / `procedure` | 调用方原样回传，便于对账 |
| `status` | 流程控制核心字段，五态：`ok` / `not_found` / `encrypted` / `too_large` / `error`（详见下方） |
| `error` | 非 `ok` 状态下的错误描述；`ok` 时为 null |
| `modify_date` | SP 最近一次修改时间（来源 `sys.objects.modify_date`）；用于识别长期未维护的祖传代码 |
| `is_encrypted` | SP 是否启用 `WITH ENCRYPTION`：`1`=是（`definition` 为 null），`0`=否 |
| `definition_total_chars` | `definition` 原始字符长度；可用于评估 LLM 上下文消耗 |
| `line_count` | `definition` 行数；体量信号，超大 SP 本身是风险信号 |
| `definition` | SP 完整原始 T-SQL 定义体；`status != ok` 时为 null |
| `notice` | 使用注意事项（提示 `definition` 是原文，含敏感风险，仅供分析） |

**`status` 五态语义**

| status | 含义 | `definition` |
|---|---|---|
| `ok` | 已成功获取定义体 | SP 原文 |
| `not_found` | SP 不存在 | null |
| `encrypted` | SP 用了 `WITH ENCRYPTION` 加密，无法解析 | null |
| `too_large` | 定义体超过 `max_definition_chars`（不截断） | null |
| `error` | RPC / 权限等异常，详见 `error` 字段 | null |

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

### 场景 E：主备同步异常 / 滞后排查
```
sync_status                         # 一次拿到 summary + 各 DB 队列 + commit_lag + issues
# 若 summary.overall_health 非 HEALTHY，进一步：
cluster_topo                        # 确认拓扑/角色与同步模式
instance_summary(address=备端)      # 确认备端是否资源/版本异常
top_requests / wait_stats_snapshot  # 若主端 transaction_delay 高，定位被同步拖慢的会话
```

### 场景 F：单个存储过程的静态风险分析
```
list_databases                              # （可选）确认 SP 所在的库
# 用户告诉你 SP 名 'dbo.dsp_DeleteUserCarePrivilegeAccount'
get_stored_procedure(
  dbname=L2MAccountDB,
  procedure="dbo.dsp_DeleteUserCarePrivilegeAccount"
)
# 根据 status 分支：
#   ok        -> 用 definition 做风险扫描（硬编码凭据 / 动态 SQL / 权限提升 / 体量信号）
#   not_found -> 反问用户库名 / SP 名是否拼写正确
#   encrypted -> 告知 LLM 该 SP 加了 WITH ENCRYPTION，无法静态分析
#   too_large -> 提示用户定义体超过 max_definition_chars，可调大上限或人工分段分析
```

### 场景 G：数据库文件容量 / 日志增长排查
```
list_databases                              # 找到目标实例上候选库
database_file_usage(databases=[A, B, C])    # 一次拿到 1~20 个库的 mdf/ldf 使用率与库级汇总
# 若某库 log_used_pct 接近 100%：
sync_status                                 # 排查是否因镜像/AG 备端落后导致日志无法截断
top_requests / blocking_sessions            # 排查长事务阻塞日志截断
```