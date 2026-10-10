# 告警类型: 连接失败 / 连接异常

## 告警解释

MySQL 连接失败告警（`db-up` 指标）表示监控系统探测到数据库实例无法正常连接。可能的含义：
- 实例不可达（网络问题、实例宕机）
- 实例连接数已满，新连接被拒绝（`Too many connections`）
- 认证失败（密码变更、权限问题）
- Proxy 层异常（proxy 进程崩溃或不可用）

这是**高优先级告警**，可能直接影响业务的数据库访问。

常见原因：
- 实例或主机故障/宕机
- 连接数打满 (`max_connections` 上限)
- 网络抖动或防火墙策略变更
- Proxy 进程异常
- 主从切换过程中的短暂不可用

## 分析步骤

### Step 1: 尝试分析当前 Processlist

调用 skill `mysql-processlist-analyzer` 分析当前实例的连接情况。

参数提取：
- `address`: 从告警中的 `instance_host` + `instance_port` 提取，格式为 `ip:port`
- 如果 `machine_type` 为 `proxy`，说明告警的是 proxy 实例，使用 `mysql_query_show_proxy_processlist`
- 如果 `machine_type` 不是 `proxy` 或未指定，使用 `mysql_query_show_mysql_processlist`

**重点关注**：
- 能否正常获取到 processlist（如果获取失败，说明实例可能仍处于不可用状态）
- 当前连接数是否接近 `max_connections`
- 是否有大量连接来自同一来源

**如果 processlist 获取失败**：记录错误信息，继续后续步骤。这本身就是重要的诊断信息。

### Step 2: 查询集群近期告警

```bash
dbm-mcp-cli call bkdbm-mcp-prod-alarm-query.alarm_query_query_monitor_alarm_info \
  body_param='{"bk_biz_id": <bk_biz_id>, "cluster_domains": ["<cluster_domain>"], "start_time": "<base_time - 20min>", "end_time": "<base_time + 20min>"}' \
  --raw-query "<用户原始问题>"
```

关注是否同时存在以下关联告警：
- Threads_running 过高（可能是连接数打满导致）
- 主从同步异常（可能发生了主从切换）
- 其他实例的连接失败（可能是集群级别的故障）

### Step 3: 查看集群拓扑和实例状态

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_mysql_cluster_topo \
  body_param='{"cluster_domain": "<cluster_domain>"}' \
  --raw-query "<用户原始问题>"
```

关注：
- 集群各实例是否都在线
- 是否发生过主从切换
- proxy 层是否正常

### Step 4: 查看实例启动时间 uptime

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_show_global_status_with_names \
  body_param='{"address": "<ip:port>", "status_names": ["uptime"]}' \
  --raw-query "<用户原始问题>"
```

判断实例是否发生过重启，如果对应时间段发生过重启，你需要进步一查询 mysql 内存使用率趋势：
```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "memory_usage", "start_time": "<base_time - 1440min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```


## 报告输出格式

### 连接状态检测

| 检查项 | 结果 |
|--------|------|
| Processlist 获取 | ✅ 成功 / ❌ 失败 (错误信息) |
| 当前连接数 | xx |
| 连接是否恢复 | 是 / 否 |

（如果 processlist 获取成功，展示 mysql-processlist-analyzer 的标准分析结果）

### 关联告警（base_time 前 10 分钟）

| 告警名称 | 时间 | 目标 | 内容 |
|---------|------|------|------|
（列出同集群的相关告警）

如无关联告警，显示：「base_time 前 10 分钟无其他关联告警」

### ️ 集群拓扑状态

展示集群当前拓扑结构和各实例状态。

### 综合判断

根据以上结果分析：
- 连接失败是否已恢复
- 可能的故障原因（实例宕机 / 连接数满 / proxy 异常 / 网络问题）
- 是否需要紧急人工介入
- 后续关注建议
