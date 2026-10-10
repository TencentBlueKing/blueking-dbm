# 告警类型: MySQL 从库延迟

## 告警解释

主从数据延迟告警（`mysql_slave_status_seconds_behind_master` 指标），表示从库复制落后主库的时间超过阈值。长时间延迟过高会影响 DBHA 故障切换的可靠性，同时也会导致从库读业务获取到过时数据。

常见原因：
- 主库写入大量数据，slave 应用追赶不上
  - 从库复制参数是否启用并行复制 `slave_parallel_type`，主库是否有开启 `group_commit`
  - 是否有设置 binlog 限速 `read_binlog_speed_limit`
- 主库 delete 数据表无主键
- 从库机器 cpu/io 性能跟不上，达到瓶颈
- 从库刚完成重建，在追赶全备后的 binlog

## 分析步骤

核心是看延迟是否有在慢慢缩小，按照以下步骤逐一排查：

### Step 1: 查看主从延迟指标

查看 base_time 前 12h 的主从延迟趋势：

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.promql_query_metrics_with_instances \
  body_param='{"cluster_domain": "<cluster_domain>", "metric_name": "mysql_slave_status_seconds_behind_master", "step": "5m", "group_by": ["instance", "master_server_id"], "instance": ["<告警延迟实例 ip:port>"], "aggregation": "max", "range_function": "max", "start_time": "<base_time - 12h>", "end_time": "<base_time>"}' \
  --raw-query "<用户原始问题>"
```

**重点关注**：
- 延迟开始的时间点
- 延迟是否持续变大（恶化）还是在慢慢缩小（恢复中）
- 延迟的峰值和当前值

### Step 2: 查看 slave 的延迟信息 (show slave status)

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_show_instance_slave_status \
  body_param='{"address": "<告警延迟实例 ip:port>", "bk_cloud_id": 0}' \
  --raw-query "<用户原始问题>"
```

**特别需要关注**：
- `Relay_Master_Log_File`: SQL 线程正在执行的 master binlog
- `Exec_Master_Log_Pos`: SQL 线程对应的 master binlog position
- `Master_Log_File`: IO 线程正在拉取的 master binlog
- `Read_Master_Log_Pos`: IO 线程对应的 master binlog position
- `Relay_Log_Space`: relay log 积压了多少
- `Master_Host`: 主库 IP
- `Master_Port`: 主库 port
- `Slave_IO_Running` / `Slave_SQL_Running`: 复制线程是否正常运行
- `Relay_Log_File`: slave 本地 relay log 当前文件名
- `Relay_Log_Pos`: slave 本地 relay log 回放的当前位点

通过对比 IO 线程和 SQL 线程的位置差距，判断瓶颈在 IO 还是 SQL 回放。


### Step 3: 查看 relay log 正在回放的事件

在 slave 节点上查看 `Relay_Log_File` 和 `Relay_Log_Pos` 位点附近对应的 binlog 事件：

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_show_relaylog_events \
  body_param='{"address": "<Slave_Host:Slave_Port>", "bk_cloud_id": 0, "log_name": "<Relay_Master_Log_File>", "from_pos": <Exec_Master_Log_Pos>, "limit_row_count": 20}' \
  --raw-query "<用户原始问题>"
```

**重点关注**：
- 如果看到有大量重复的 Event_type（比如 `Delete_rows`），可能是在批量操作数据引起的
- 是否有大事务（单个事务跨越多个 binlog position）
- 操作的目标表是什么 (Table_map 行)

### Step 4: 查看 CPU 和 IO 负载

#### 4.1 查看 master 和 slave 的 CPU 负载

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.promql_query_metrics_with_instances \
  body_param='{"cluster_domain": "<cluster_domain>", "metric_name": "cpu_summary:usage", "step": "5m", "group_by": ["instance", "master_server_id"], "instance": ["<master ip:port>", "<slave ip:port>"], "aggregation": "max", "range_function": "max", "start_time": "<base_time - 12h>", "end_time": "<base_time>"}' \
  --raw-query "<用户原始问题>"
```

#### 4.2 查看 master 和 slave 的读 IO 吞吐（单位 kb/s）

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.promql_query_metrics_with_instances \
  body_param='{"cluster_domain": "<cluster_domain>", "metric_name": "io.rkb_s", "step": "1m", "group_by": ["bk_target_ip", "instance_role"], "instance": ["<master ip:port>", "<slave ip:port>"], "aggregation": "max", "range_function": "max", "start_time": "<base_time - 1h>", "end_time": "<base_time>"}' \
  --raw-query "<用户原始问题>"
```

#### 4.3 查看 master 和 slave 的写 IO 吞吐（单位 kb/s）

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.promql_query_metrics_with_instances \
  body_param='{"cluster_domain": "<cluster_domain>", "metric_name": "io.wkb_s", "step": "1m", "group_by": ["bk_target_ip", "instance_role"], "instance": ["<master ip:port>", "<slave ip:port>"], "aggregation": "max", "range_function": "max", "start_time": "<base_time - 1h>", "end_time": "<base_time>"}' \
  --raw-query "<用户原始问题>"
```

**重点关注**：
- 从库 CPU 是否打满（说明 SQL 线程回放成为瓶颈）
- 从库 IO 是否很高（可能磁盘成为瓶颈）
- 主库写入量是否异常增大（大批量写入导致从库追不上）

### Step 5: 综合分析

基于以上收集的信息，判断：
- 主从延迟的根因
- 延迟趋势是恶化还是在恢复
- 是否需要人工介入处理

## 报告输出格式

### 主从延迟趋势（过去 12 小时）

| 时间点 | 延迟(秒) | 趋势 |
|--------|----------|------|
（展示关键时间点的延迟值，标注延迟开始时间和趋势方向）

- 延迟开始时间: `<time>`
- 延迟趋势: 持续增大 / 趋于稳定 / 逐步恢复

### 复制状态 (Slave Status)

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Slave_IO_Running | Yes / No | IO 线程 |
| Slave_SQL_Running | Yes / No | SQL 线程 |
| Master_Host | `<ip>` | 主库 IP 地址 |
| Master_Port | `<port>` | 主库端口 |
| Relay_Master_Log_File | `<file>` | SQL 线程对应主库 binlog 文件名 |
| Exec_Master_Log_Pos | `<pos>` | SQL 线程对应主库 binlog 位置 |
| Master_Log_File | `<file>` | IO 线程对应主库 binlog 文件名 |
| Read_Master_Log_Pos | `<pos>` | IO 线程对应主库 binlog 位置 |
| Relay_Log_Space | `<size>` | relay log 占用的磁盘空间（积压量） |

### Binlog 事件分析

展示 master 上 slave 正在执行位置的 binlog 事件内容，分析是否有大批量操作。

如果在 `Step 3: 查看 master binlog 事件` 中，看到有大量重复的 Event_type（比如 `Delete_rows`），可以从 Table_map 中看到库表名，报告结束可以询问用户是否需要看下这个库表结构。

### 资源使用情况

#### CPU 使用率

| 实例 | 角色 | CPU 使用率 |
|------|------|-----------|
（展示 master 和 slave 的 CPU 使用情况）

#### IO 吞吐

| 实例 | 角色 | 读 IO (kb/s) | 写 IO (kb/s) |
|------|------|-------------|-------------|
（展示 master 和 slave 的 IO 使用情况）

### 综合判断

根据以上结果分析：
- 延迟的根本原因（大批量写入 / 无主键删除 / 从库性能瓶颈 / 重建追赶中）
- 延迟趋势判断（是否在恢复）
- 建议的处理措施
