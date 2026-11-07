# 告警类型: MySQL 主机 CPU 负载过高

## 告警解释

MySQL 主机的 CPU 使用率持续超过阈值（通常 ≥ 90%），说明实例所在主机的计算资源已接近耗尽，可能导致：
- SQL 执行变慢，响应时间显著增大
- 新连接建立缓慢或超时
- 实例出现卡顿甚至不可用

常见原因：
- 慢 SQL / 大查询消耗大量 CPU
- 业务流量突增，QPS 暴涨
- 锁等待导致线程堆积，CPU 空转
- 未命中索引的全表扫描

**核心关注点**：找到导致 CPU 飙高的根因 SQL 或流量变化。

## 关键字段提取

从告警维度中提取以下关键信息：

| 字段 | 来源 | 说明 |
|------|------|------|
| `target_ip` | `目标` 或 `目标IP` 维度 | 告警主机 IP |
| `cluster_domain` | `cluster_domain` 维度 | 集群域名 |
| `instance_role` | `instance_role` 维度 | 实例角色（如 backend_master） |
| `bk_biz_id` | `所属空间` 中的 `[数字]` | 业务 ID |
| `cluster_type` | `cluster_type` 维度或从告警上下文推断 | 集群类型（tendbha / tendbcluster） |
| `app` / `appid` | 维度中的字段 | 业务名/业务 ID |
| `current_value` | `内容` 字段中的 `当前值` | 当前 CPU 使用率 |

**实例地址构造**：
- 告警中给出的是主机 IP（`target_ip`），需要先调用 `mysql_query_mysql_cluster_topo` 查询拓扑获取准确的 ip:port, instance_role 信息

## 分析步骤

### Step 1: 查看 CPU 负载趋势

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "cpu_summary", "start_time": "<base_time - 30min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```

**分析要点**：
- CPU 是突增还是缓慢爬升
- 是否在某个时间点出现拐点（对应可能的触发事件）
- 当前值是否仍在高位

### Step 2: 查看 QPS 请求量趋势

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "qps_summary", "start_time": "<base_time - 30min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```

**分析要点**：
- QPS 是否与 CPU 趋势同步上升（流量突增导致 CPU 高）
- QPS 平稳但 CPU 飙高（说明是慢 SQL / 大查询导致，而非流量问题）
- QPS 是否有异常波动

### Step 3: 查看当前连接会话情况

mysql_query_show_instance_processlist_aggregated 可以看任何 instance_role (proxy,backend_*, remote_*, spider_*) 的 processlist

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_query_show_instance_processlist_aggregated \
  body_param='{"instance": "<ip:port>", "aggregate_type": ["group_by_state", "group_by_fingerprint"]}' \
  --raw-query "<用户原始问题>"
```

`instance` 从告警字段构造（见"关键字段提取"中的实例地址构造方式）。

**分析要点**：
- `group_by_state`: 查看连接处于什么状态
  - 大量 `Sending data` / `executing` → 查询消耗 CPU
  - 大量 `Locked` / `Waiting for table metadata lock` → 锁等待
  - 大量 `Creating sort index` / `Sorting result` → 排序操作消耗 CPU
- `group_by_fingerprint`: 查看哪类 SQL 最多
  - 是否有某个 SQL 指纹大量堆积（可能是慢 SQL 的根因）
  - 高频 SQL 是否为预期内的业务查询

### Step 4: 查看慢查询情况

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-slowlog.mysql_slowlog_query_aggregated \
  body_param='{"cluster_domain": "<cluster_domain>", "instance_role": "<instance_role>", "metric_name": "query_time_max", "limit": 10, "start_time": "<base_time - 30min>", "end_time": "<base_time + 10min>"}' \
  --raw-query "<用户原始问题>"
```

`instance_role` 从告警实例角色推断（如 `backend_master`）。

**分析要点**：
- 是否有执行时间特别长的慢 SQL（query_time 大）
- 是否有扫描行数特别多的 SQL（rows_examined 大，可能缺少索引）
- 慢 SQL 的执行频率是否很高（count 大）
- 慢 SQL 出现的时间是否与 CPU 飙高时间吻合

## 报告输出格式

在完成上述步骤后，按以下格式汇总输出：

### 故障概要

| 字段 | 值 |
|------|-----|
| 告警类型 | MySQL 主机 CPU 负载过高 |
| 主机 IP | `<target_ip>` |
| 实例角色 | `<instance_role>` |
| 集群域名 | `<cluster_domain>` |
| 集群类型 | `<cluster_type>` |
| 当前 CPU | `<current_value>` |
| 告警时间 | `<base_time>` |

### CPU & QPS 趋势（base_time 前 30 分钟）

| 指标 | 趋势描述 | 起始值 | 峰值 | 告警时值 |
|------|---------|--------|------|---------|
| CPU 负载 | 上升/平稳/突增 | xx% | xx% | xx% |
| QPS | 上升/平稳/突增 | xx | xx | xx |

用趋势文字或简易图示说明 CPU 和 QPS 的关联关系。

### 连接会话分析

#### 按 State 聚合

| State | 连接数 | 说明 |
|-------|--------|------|
| ... | ... | ... |

#### 按 SQL 指纹聚合

| SQL 指纹 | 连接数 | 说明 |
|----------|--------|------|
| ... | ... | ... |

### 慢查询 Top N（base_time 前 30 分钟）

| # | SQL 指纹 | 最大耗时 | 执行次数 | 扫描行数 |
|---|---------|---------|---------|---------|
（从慢查询结果中提取）

### 综合结论

根据以上多维度数据，综合分析：
1. CPU 飙高的核心原因（慢 SQL / 流量突增 / 锁等待 / 其它）
2. 与 CPU 飙高关联最大的 SQL 或行为
3. 当前是否仍在持续
4. 建议的处理措施（按优先级排列）
5. 是否需要进一步人工介入
