---
name: dbm-mysql-alarm-analyzer
description: MySQL 告警智能分析。当用户转发告警信息、要求分析告警、排查 Threads_running 高、慢查询过多、连接失败、CPU 负载高、DBHA 故障切换、长空闲事务、MySQL hang、从库延迟、磁盘空间使用率高、DBHA 探测失败等 MySQL 告警时触发。用户消息中包含告警标题特征（如 [致命]、 [预警]、 首次异常时即视为转发告警。
metadata: {"version":"1.0.3","space_id":"1d3d86fa67bef8c3","bk_skill_code":"dbm-mysql-alarm-analyzer","is_public":false,"bkai-dependencies":{"envs":[{"key":"DBM_MCPS","description":"dbm mcp server 地址列表","required":true,"default":"bkdbm-mcp-prod-alarm-query bkdbm-mcp-prod-mysql-capacity bkdbm-mcp-prod-mysql-metrics bkdbm-mcp-prod-mysql-query bkdbm-mcp-prod-mysql-slowlog bkdbm-mcp-prod-ticket-op bkdbm-mcp-prod-bkjob-wrap","secret":false},{"key":"OUTPUT_DIR","description":"skills 产物输出路径","required":false,"default":".storage/session","secret":false}]}}
---

# MySQL 告警智能分析

当用户转发 MySQL 告警信息时，自动识别告警类型并执行对应的分析流程。

只要用户要求分析，不用管是否之前已有重复分析，也不用汇总历史会话的告警分析，每次都是一次独立的告警分析。

## Workflow

### Step 1: 解析告警信息

从用户转发的告警文本中提取以下关键字段：

| 字段 | 来源 | 说明 |
|------|------|------|
| `alarm_type` | 标题行（如 `TendbCluster 实例 Threads_running`） | 用于匹配告警类型 |
| `severity` | `[致命]` / `[预警]` / `[提醒]` | 告警级别 |
| `first_anomaly_time` | `首次异常` 字段 | 告警开始时间 |
| `last_anomaly_time` | `最近异常` 字段 | 最近一次异常时间 |
| `content` | `内容` 字段 | 告警详细描述，含当前值 |
| `bk_biz_id` | `所属空间` 中的 `[数字]` | 业务 ID |
| `cluster_domain` | `cluster_domain` 维度 | 集群域名 |
| `instance` | `instance` 或 `instance_host + instance_port` | 实例地址 (ip:port 或 ip-port) |
| `instance_role` | `instance_role` 维度 | 实例角色 |
| `app` / `appid` | 维度中的字段 | 业务名/业务 ID |
| `server_ip` | `server_ip` 维度 | 故障机器 IP（DBHA 告警特有） |
| `server_port` | `server_port` 维度 | 故障机器端口（DBHA 告警特有） |
| `machine_type` | `machine_type` 维度 | 机器类型（proxy / backend） |
| `cluster_type` | `cluster_type` 维度 | 集群类型（tendbha / tendbcluster） |

**地址格式转换**：告警中的实例地址可能是 `ip-port` 格式，调用 `dbm-mcp-cli` 时需要转换为 `ip:port` 格式。

### Step 2: 识别告警类型 & 加载处理方法

根据告警标题中的关键词匹配告警类型，然后 **使用 `read_file` 加载对应的 references 文件**，按照其中的步骤执行分析：

| 告警关键词 | 告警类型 | References 文件 |
|-----------|---------|----------------|
| `Threads_running` | 活跃线程数过高 | `{SKILL_DIR}/references/alarm_threads_running.md` |
| `慢查询数量` / `slow_queries` | 慢查询数量过多 | `{SKILL_DIR}/references/alarm_slow_queries.md` |
| `连接失败` / `db-up` / `连接数` | 连接异常 | `{SKILL_DIR}/references/alarm_connection.md` |
| `dbha` / `二次探测` / `doublecheck` | DBHA 二次探测失败（机器故障切换） | `{SKILL_DIR}/references/alarm_dbha_doublecheck.md` |
| `CPU` / `cpu` / `CPU使用率` / `CPU负载` | MySQL 主机 CPU 负载过高 | `{SKILL_DIR}/references/alarm_cpu_high.md` |
| `空闲事务` / `idle` / `innodb_trx_idle_time` | 长空闲事务未关闭 | `{SKILL_DIR}/references/alarm_long_idle_trx.md` |
| `hang` / `may be hang` / `db-hang` | MySQL may be hang | `{SKILL_DIR}/references/alarm_mysql_hang.md` |
| `从库延迟` / `slave_delay` / `seconds_behind_master` / `主从延迟` | 同步延迟 | `{SKILL_DIR}/references/alarm_slave_delay.md` |
| `磁盘空间` / `disk` / `磁盘使用率` / `disk_usage` | 磁盘空间使用率过高 | `{SKILL_DIR}/references/alarm_disk_space.md` |

如果告警类型无法匹配上述任何一种，输出：

> ⚠️ 暂不支持该告警类型的自动分析，请提供更多信息或手动排查。

然后列出告警中解析到的字段供用户参考。

### Step 3: 执行分析（由 references 文件定义）

加载对应的 references 文件后，严格按照其中定义的步骤执行分析。每个 references 文件包含：

1. **告警解释** — 说明告警含义和可能的影响
2. **分析步骤** — 需要调用的 `dbm-mcp-cli` 命令 / skill 及其参数
3. **汇总模板** — 最终输出的分析报告格式

### Step 4: 输出分析报告

所有分析步骤执行完毕后，按以下结构输出报告：

---

**## 告警分析报告**

**告警类型**: `<alarm_type>`
**告警级别**: `<severity>`
**集群域名**: `<cluster_domain>`
**告警实例**: `<instance>`
**告警时间**: `<first_anomaly_time>`

---

（各分析步骤的结果，格式由 references 文件定义）

---

**## 综合诊断与建议**

根据以上所有分析结果，给出综合判断：
1. 当前症状是否仍在持续
2. 可能的根因分析
3. 建议的处理措施（按优先级排列）
4. 是否需要进一步人工介入

---

## 从告警维度提取集群类型

根据告警维度信息推断 `cluster_type`，供 `dbm-mcp-cli` 调用时使用：

| 判断依据 | cluster_type |
|---------|-------------|
| 标题含 `TendbCluster` 或域名以 `spider.` 开头 | `tendbcluster` |
| 标题含 `TenDBHA` 或 instance_role 含 `backend_` | `tendbha` |
| 标题含 `TenDBSingle` | `tendbsingle` |
| 无法判断时 | 从域名特征推断，或调用 `mysql_query_mysql_cluster_topo` 查询 |

## 时间窗口约定

时间基准点（`base_time`）：优先使用告警中的 `最近异常` 时间（即 `last_anomaly_time`）；如果告警中没有该字段，则以当前时间为基准。

分析时的默认时间窗口：
- **metrics 查询**: `base_time - 30min` 到 `base_time`
- **慢查询查询**: `base_time - 1h` 到 `base_time`
- **告警查询**: `base_time - 10min` 到 `base_time`
- 时间格式统一使用 ISO 8601: `2026-04-10T02:12:00+08:00`

## Glossary

For DBM-specific terminology (cluster types, instance roles, etc.), refer to `{SKILL_DIR}/references/dbm_glossary.md`.
