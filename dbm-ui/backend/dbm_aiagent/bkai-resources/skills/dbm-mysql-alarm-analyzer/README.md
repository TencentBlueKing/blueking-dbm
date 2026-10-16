# mysql-alarm-analyzer

MySQL 告警智能分析，自动识别告警类型并执行多维度诊断。

## 功能

用户转发 MySQL 告警文本后，自动解析告警内容、识别告警类型、加载对应的分析流程，调用 `dbm-mcp-cli` 和相关 skill 采集数据，最终输出诊断报告和处理建议。

## 支持的告警类型

| 告警类型 | 关键词 | References 文件 |
|---------|--------|----------------|
| 活跃线程数过高 | `Threads_running` | `alarm_threads_running.md` |
| 慢查询数量过多 | `慢查询数量` / `slow_queries` | `alarm_slow_queries.md` |
| 连接异常 | `连接失败` / `db-up` / `连接数` | `alarm_connection.md` |
| DBHA 故障切换 | `dbha` / `二次探测` / `doublecheck` | `alarm_dbha_doublecheck.md` |
| CPU 负载过高 | `CPU` / `CPU使用率` / `CPU负载` | `alarm_cpu_high.md` |
| 长空闲事务未关闭 | `空闲事务` / `idle` / `innodb_trx_idle_time` | `alarm_long_idle_trx.md` |
| MySQL may be hang | `hang` / `may be hang` / `db-hang` | `alarm_mysql_hang.md` |

## 目录结构

```
mysql-alarm-analyzer/
├── SKILL.md                                # skill 主文件（告警解析、路由、报告格式）
├── references/
│   ├── alarm_threads_running.md            # Threads_running 告警分析流程
│   ├── alarm_slow_queries.md               # 慢查询数量告警分析流程
│   ├── alarm_connection.md                 # 连接失败告警分析流程
│   ├── alarm_dbha_doublecheck.md           # DBHA 故障切换告警分析流程
│   ├── alarm_cpu_high.md                   # CPU 负载告警分析流程
│   ├── alarm_long_idle_trx.md              # 长空闲事务告警分析流程
│   ├── alarm_mysql_hang.md                 # MySQL hang 告警分析流程
│   └── dbm_glossary.md                     # DBM 术语表
└── README.md
```

## 使用的 dbm-mcp-cli 接口

| 接口 | 用途 |
|---|---|
| `mysql_metrics_query_by_metric_name` (metric_name=cpu_summary) | CPU 负载趋势 |
| `mysql_metrics_query_by_metric_name` (metric_name=qps_summary) | QPS 趋势 |
| `mysql_metrics_query_by_metric_name` (metric_name=connections) | 连接数趋势 |
| `mysql_slowlog_query_aggregated` | 慢查询聚合列表 |
| `mysql_query_mysql_cluster_topo` | 集群拓扑状态 |
| `mysql_query_show_instance_processlist_aggregated` | 连接会话聚合 |
| `mysql_query_show_global_status_with_names` | 实例状态变量 |
| `alarm_query_query_monitor_alarm_info` | 关联告警查询 |
| `mysql_query_trx_long_running` | 长事务查询 |
| `mysql_query_show_proxy_processlist` | Proxy processlist 查询 |

## 依赖的 skill

| skill | 用途 |
|---|---|
| `mysql-processlist-analyzer` | Threads_running / 连接失败告警中分析 processlist |
| `mysql-slow-query-tuning` | 慢查询数量告警中执行深度慢查询分析 |

## 贡献指南

新增一种告警类型：

1. 在 `references/` 下创建 `alarm_<告警名>.md`，包含告警解释、分析步骤、报告输出格式
2. 在 `SKILL.md` Step 2 路由表中添加对应条目
3. 运行 `dev-skills/check-skill-compliance` 验证合规性
