# 告警类型: Threads_running 活跃线程数过高

## 告警解释

MySQL 实例中 `Threads_running` 指标表示当前正在执行 SQL 的线程数量。当该值过高时（通常阈值 ≥ 500），说明实例中同时运行的 SQL 过多，可能导致：
- 实例响应时间显著增大
- CPU 负载飙高
- 新请求排队等待，应用出现超时

常见原因：
- 突发流量/请求量暴增
- 慢 SQL 堆积，占用大量线程
- 锁等待/死锁导致 SQL 执行缓慢
- 后端存储 IO 瓶颈

## 分析步骤

### Step 1: 分析当前 Processlist

读取 `./references/alarm_threads_running/mysql-processlist-analyzer.md` ，根据里面的步骤来分析当前实例的 SQL 执行情况。


重点关注：
- 是否有大量相同 fingerprint 的 SQL（可能是慢 SQL 堆积）
- 是否有长时间运行的查询
- 连接来源是否集中在某些 IP

### Step 2: 查看 CPU 负载趋势

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "cpu_summary", "start_time": "<base_time - 30min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```

### Step 3: 查看连接数变化趋势

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "connections", "start_time": "<base_time - 30min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```

### Step 4: 查看 QPS 请求量变化趋势

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "qps_summary", "start_time": "<base_time - 30min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```

### Step 5: 查看慢查询情况

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-slowlog.mysql_slowlog_query_aggregated \
  body_param='{"cluster_domain": "<cluster_domain>", "instance_role": "<instance_role>", "metric_name": "query_time_max", "limit": 5, "start_time": "<base_time - 30min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```

`instance_role` 从告警实例角色推断（如 `backend_master`、`spider_master`）。

## 报告输出格式

在完成上述步骤后，按以下格式汇总输出（嵌入 Step 4 报告模板中）：

### Processlist 分析
（使用 mysql-processlist-analyzer 的标准输出格式）

### 性能指标趋势（base_time 前 30 分钟）

| 指标 | 趋势描述 | 当前值 | 峰值 |
|------|---------|--------|------|
| CPU 负载 | 上升/平稳/下降 | xx% | xx% |
| 连接数 | 上升/平稳/下降 | xx | xx |
| QPS | 上升/平稳/下降 | xx | xx |

### 慢查询 Top 10

| # | SQL 指纹 | 最大耗时 | 执行次数 | 扫描行数 |
|---|---------|---------|---------|---------|
（从慢查询结果中提取）

### 综合判断

根据以上多维度数据，综合分析：
- Threads_running 是否仍处于高位
- 是否与慢 SQL 堆积相关
- 是否与流量突增相关
- 建议的处理措施
