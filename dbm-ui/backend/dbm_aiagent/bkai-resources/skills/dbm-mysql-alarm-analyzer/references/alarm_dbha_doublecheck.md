# 告警类型: DBHA 二次探测失败（机器故障切换）

## 告警解释

DBHA（Database High Availability）是 MySQL 高可用系统。当 DBHA 对实例进行第一次故障探测失败后，会发起二次探测，如果二次探测仍然失败，则判定为真实故障，随后触发自动切换动作。

收到此告警意味着：
- DBHA 已确认目标实例发生了真实故障（非误报）
- 自动切换流程**已经触发或即将触发**
- 需要关注切换是否成功完成

**核心关注点**：切换是否成功，业务是否已恢复正常访问。

## 关键字段提取

从告警维度中提取以下关键信息：

| 字段 | 来源 | 说明 |
|------|------|------|
| `faulty_ip` | `server_ip` 维度 | **故障机器 IP**（最关键字段） |
| `faulty_port` | `server_port` 维度 | 故障机器端口 |
| `cluster_domain` | `cluster_domain` 维度 | 集群域名 |
| `cluster_type` | `cluster_type` 维度 | 集群类型（tendbha / tendbcluster） |
| `machine_type` | `machine_type` 维度 | 故障机器类型（proxy / backend） |
| `instance_role` | `instance_role` 维度 | 故障之前机器的角色。故障之后角色可能会发生变化，比如主故障后会切为从 |
| `bk_biz_id` | `所属空间` 中的 `[数字]` | 业务 ID |

## 分析步骤

### Step 1: 查看集群当前拓扑结构

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_mysql_cluster_topo \
  body_param='{"cluster_domain": "<cluster_domain>"}' \
  --raw-query "<用户原始问题>"
```

**分析要点**：

- 故障机器（`faulty_ip`）的状态应该显示为 `不可用` / `unavailable`
- **如果故障的是存储层节点（backend）**：
  - 主节点（backend_master）必须是 `运行中` / `running` 状态
  - 记录当前新主节点的地址：`current_master_ip:port`（存储层 新主节点）
- **如果故障的是接入层节点（proxy）**：
  - 必须有其它接入层节点处于 `运行中` / `running` 状态，不能全部故障
  - 记录当前 running 状态的接入层地址：current_proxy_ip_list + port

### Step 2: 查询切换相关告警

```bash
dbm-mcp-cli call bkdbm-mcp-prod-alarm-query.alarm_query_query_monitor_alarm_info \
  body_param='{"bk_biz_id": <bk_biz_id>, "cluster_domains": ["<cluster_domain>"], "start_time": "<base_time - 20min>", "end_time": "<base_time + 20min>"}' \
  --raw-query "<用户原始问题>"
```

**关键判断**：

- 需要在告警列表中看到 **"Mysql dbha切换mysql成功"** 且 `server_ip` 包含故障 IP 的告警记录
- 如果找到切换成功告警 → 切换已完成
- 如果**未找到**切换成功告警 → 切换可能失败或仍在进行中，**需要紧急人工介入**，可能会长时间影响业务访问


### Step 3: 查看故障前后 QPS 趋势

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-metrics.mysql_metrics_query_by_metric_name \
  body_param='{"cluster_domain": "<cluster_domain>", "cluster_type": "<cluster_type>", "metric_name": "qps_summary", "start_time": "<base_time - 20min>", "end_time": "<base_time + 20min>"}' \
  --raw-query "<用户原始问题>"
```

**分析要点**：
- tendbha 机器故障：关注角色为 `backend_master` 的 QPS
- tendbcluster 机器故障：关注角色为 `spider_master` 的 QPS
- 对比故障前后的 QPS 水平，确认是否已恢复到故障前的正常水平
- 如果 QPS 明显下降且未恢复，说明业务可能仍受影响

### Step 4: 看是否有发起故障机器的替换自愈单据

```
dbm-mcp-cli call bkdbm-mcp-prod-ticket-op.ticket_op_ticket_list \
  body_param='{"cluster_domains": ["<cluster_domain>"], "bk_biz_id": <bk_biz_id>, "time_duration": "01:00:00"}'
```

time_duration 表示当前时间的前 1 小时。看最近一小时的单据记录，如果有自愈单据，但单据是失败状态，需要提示人工介入。

## 报告输出格式

### 故障概要

| 字段 | 值 |
|------|-----|
| 故障类型 | DBHA 二次探测失败（机器故障） |
| 故障 IP | `<faulty_ip>` |
| 故障端口 | `<faulty_port>` |
| 机器类型 | `<machine_type>` |
| 集群域名 | `<cluster_domain>` |
| 集群类型 | `<cluster_type>` |

### 集群拓扑状态

展示集群当前各节点的角色、IP、端口、状态，标注故障节点和新主节点。

### 切换结果判定

| 检查项 | 结果 |
|--------|------|
| 故障节点状态 | `不可用` / 其它 |
| 切换成功告警 | 找到 / 未找到 |
| 切换结论 | 切换成功 / 切换可能失败（需人工介入） |

### 切换后连接验证

展示 mysql_query_show_instance_processlist_aggregated 对正常实例的分析结果（按 user 维度聚合）。

### QPS 恢复情况

| 时间段 | QPS 水平 |
|--------|---------|
| 故障前（base_time - 20min ~ base_time） | xx |
| 故障后（base_time ~ base_time + 20min） | xx |
| 是否恢复 | 是 / 否 |

### 综合结论

根据以上所有分析结果，给出简明结论：
1. 切换是否成功
2. 业务是否已恢复正常
3. 是否需要进一步人工处理
4. 后续建议（如：确认故障机器回收、检查备份、补充从库等）
