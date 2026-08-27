# 告警类型: MySQL may be hang

## 告警解释

`db-hang` 告警表示 mysql-monitor 本地监控在尝试连接 MySQL 实例时**超时无响应**。这意味着 MySQL 进程可能处于挂起状态（hang），无法处理新的连接请求。

**严重程度**：**致命**。这通常意味着实例已完全不可用，业务访问会受到直接影响。

常见原因：
- MySQL 内部死锁或 latch 竞争导致线程全部阻塞
- 大量并发请求导致线程堆积，MySQL 无法调度
- 磁盘 I/O 完全阻塞（如存储故障）
- 操作系统级别的问题（OOM、内核 bug）
- MySQL bug 导致进程挂起

## 参数提取

| 参数 | 来源 | 说明 |
|------|------|------|
| `address` | 告警维度 `instance_host` + `instance_port` | 格式 `ip:port` |
| `cluster_domain` | 告警维度 `cluster_domain` | 集群域名 |
| `cluster_type` | 告警标题或维度推断 | tendbha / tendbcluster / tendbsingle |
| `base_time` | 告警中的「最近异常」时间 | 作为所有时间窗口的基准终点 |

## 分析步骤

### Step 1: 查看当前 Processlist 情况

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_show_instance_processlist_aggregated \
  body_param='{"address": "<ip:port>", "aggregate_types": ["group_by_state"]}' \
  --raw-query "<用户原始问题>"
```

- `aggregate_types`: 只传 `["group_by_state"]`

**重点关注**：
- **如果 processlist 获取失败**：说明实例当前仍然无法连接，情况严重，需紧急人工介入
- 如果能获取到：查看各 state 的连接分布，是否有大量连接处于同一状态（如 `Waiting for table metadata lock`、`Sending data`、`Opening tables` 等）

### Step 2: 查看连接数变化趋势

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "connections", "start_time": "<base_time - 30min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```

**分析要点**：
- 连接数是否在故障前突然飙升
- 是否达到 max_connections 上限
- 连接数趋势是否与 hang 时间点吻合

### Step 3: 查看 QPS 变化趋势

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "qps_summary", "start_time": "<base_time - 30min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```

**分析要点**：
- QPS 是否在某个时间点突然降为 0（MySQL 完全 hang 住）
- 还是 QPS 逐渐下降（线程堆积过程）
- QPS 下降与连接数上升的时间关系

## 报告输出格式

### 实例连接状态

| 检查项 | 结果 |
|--------|------|
| Processlist 获取 | ✅ 成功 / ❌ 失败 (实例仍不可连接) |
| 连接状态分布 | （按 state 分组展示） |

⚠️ **如果 Processlist 获取失败**，在此处醒目提示：

> **实例当前仍然无法连接，MySQL 可能仍处于 hang 状态，需要紧急人工介入！**

### 连接数趋势

简要描述连接数变化趋势，标注异常拐点。

### QPS 趋势

简要描述 QPS 变化趋势，标注异常拐点。

### 综合判断

根据以上结果分析：
1. MySQL 是否仍处于 hang 状态
2. 可能的触发原因（线程堆积 / 锁等待 / 存储故障 / 连接打满）
3. 建议的紧急处理措施：
   - 如实例仍不可连接：建议紧急人工介入，考虑 kill 问题连接或重启实例
   - 如实例已恢复：分析触发原因，建议优化以避免再次发生
4. 后续关注建议
