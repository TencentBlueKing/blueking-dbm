# MySQL Processlist 分析

## 模式判断

- **集群模式**：用户提供集群域名（`cluster_domain`）→ 先查拓扑，再逐实例抓取
- **单实例模式**：用户提供 `ip:port` → 直接抓取该实例

参数提取：
- `address`: 从告警中的 `instance` 字段提取，格式转换为 `ip:port`
- 如果 `instance_role` 为 `spider_master`，实例类型为 spider（非 proxy），使用 `mysql_query_show_mysql_processlist`

## 集群模式

### 第一步：获取集群拓扑

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_mysql_cluster_topo \
  body_param='{"cluster_domain": "<cluster_domain>"}' \
  --raw-query "<用户原始问题>"
```

从返回结果中提取：
- 集群类型（`cluster_type`）：`tendbha` 或 `tendbcluster`
- 所有 MySQL 实例的 `ip`、`port`、`bk_cloud_id`、`instance_role`
- 所有接入层实例（Proxy/Spider）的 `ip`、`port`、`bk_cloud_id`

### 第二步：并行抓取 processlist

对每个 **MySQL 实例**：

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_show_mysql_processlist \
  body_param='{"bk_cloud_id": <bk_cloud_id>, "address": "<ip:port>"}' \
  --raw-query "<用户原始问题>" \
  > $OUTPUT_DIR/pl_raw_<ip>_<port>.json
```

对接入层实例，根据集群类型选择工具：

- **TenDBHA Proxy** → `mysql_query_show_proxy_processlist`
- **TenDBCluster Spider** → `mysql_query_show_mysql_processlist`

```bash
# Proxy
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_show_proxy_processlist \
  body_param='{"bk_cloud_id": <bk_cloud_id>, "address": "<ip:port>"}' \
  --raw-query "<用户原始问题>" \
  > $OUTPUT_DIR/pl_raw_<ip>_<port>.json
```

文件命名：`$OUTPUT_DIR/pl_raw_<ip>_<port>.json`（IP 中 `.` 替换为 `_`）。所有实例可并行调用。

### 第三步：验证并提取

对每个临时文件执行：

```bash
python3 ./references/alarm_threads_running/scripts/check_mcp_response.py $OUTPUT_DIR/pl_raw_<ip>_<port>.json --out $OUTPUT_DIR/pl_<ip>_<port>.json
```

失败则跳过该实例并记录错误，继续处理其余实例。

### 第四步：结构化分析

对每个提取后的文件执行：

```bash
python3 ./references/alarm_threads_running/scripts/analyze_processlist.py $OUTPUT_DIR/pl_<ip>_<port>.json --type all
```

合并所有实例的分析结果一起输出，不逐文件展示。

### 第五步：补充分析

对每个提取后的文件执行：

```bash
python3 ./references/alarm_threads_running/scripts/analyze_processlist.py $OUTPUT_DIR/pl_<ip>_<port>.json --type sample
```

`sample` 输出最多 30 条活跃连接（排除 Sleep 和系统用户，按耗时降序）的完整字段。读取这些明细，结合第四步的结构化结果，自由分析固定维度未覆盖的模式，例如：

- 多条查询是否在操作同一张表或同一类数据
- 同一来源 IP 的连接是否全在执行相似 SQL
- 是否存在异常 state 组合（如大量 `Creating sort index` 暗示缺索引）
- 连接的 user + db + fingerprint 三者组合是否揭示特定业务行为

如果 `sample` 无新发现，跳过即可，不要硬凑内容。

### 第六步：清理

```bash
rm -f $OUTPUT_DIR/pl_raw_*.json $OUTPUT_DIR/pl_*.json
```

## 单实例模式

### 第一步：抓取

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_show_mysql_processlist \
  body_param='{"address": "<ip:port>", "bk_cloud_id": 0}' \
  --raw-query "<用户原始问题>" \
  > $OUTPUT_DIR/pl_raw_<ip>_<port>.json
```

Proxy 实例使用 `mysql_query_show_proxy_processlist`。`bk_cloud_id` 未指定时默认 `0`。

### 第二步：验证并提取

```bash
python3 ./references/alarm_threads_running/scripts/check_mcp_response.py $OUTPUT_DIR/pl_raw_<ip>_<port>.json --out $OUTPUT_DIR/pl_<ip>_<port>.json
```

失败则终止并告知用户。

### 第三步：结构化分析

```bash
python3 ./references/alarm_threads_running/scripts/analyze_processlist.py $OUTPUT_DIR/pl_<ip>_<port>.json --type summary
```

可用分析维度：
| 类型 | 说明 |
|------|------|
| `summary` | 概览 + Top 用户/IP/指纹/库 + 最长连接 + 锁等待（默认） |
| `all` | 全部维度（含 state 分布） |
| `group_by_fingerprint` | SQL 指纹聚合 |
| `group_by_state` | 状态分布 |
| `group_by_user` | 用户聚合 |
| `group_by_client_host` | 来源 IP 聚合 |
| `group_by_db` | 库名聚合 |
| `lock_wait` | 锁等待检测 |
| `longest_top_5` | 最长运行查询 |
| `sample` | 活跃连接采样（最多 30 条），供自由分析 |

### 第四步：补充分析

```bash
python3 ./references/alarm_threads_running/scripts/analyze_processlist.py $OUTPUT_DIR/pl_<ip>_<port>.json --type sample
```

读取 `sample` 输出的活跃连接明细，结合第三步的结构化结果，自由分析固定维度未覆盖的模式。如果无新发现则跳过。

### 第五步：清理

```bash
rm -f $OUTPUT_DIR/pl_raw_<ip>_<port>.json $OUTPUT_DIR/pl_<ip>_<port>.json
```

## 输出格式

读取脚本 JSON 输出，按以下格式呈现。禁止直接输出原始 JSON。

```
## 实例 <address>（<角色>）Processlist 分析

### 连接概览
总连接数: N
| Command | 数量 | 占比 |
|---------|------|------|
（来自 overview.by_command）

### Top SQL 指纹
| # | 次数 | 平均耗时(s) | SQL 指纹 |
|---|------|-------------|----------|
（来自 top_fingerprints，指纹截断 80 字符）

### Top 用户 / Top 来源 IP / Top 数据库
（表格展示 count + 占比）

### 最长运行连接
[N] 执行时间: Xs  用户: <user>  库: <db>  来源: <host>
    状态: <state>
    SQL: <截断 80 字符>

### 锁等待
（lock_wait.count = 0 → "无锁等待"；否则列出详情）

### 补充分析（来自 sample）
（基于活跃连接明细的自由分析。无发现则省略本节。）

### 诊断与建议
- 综合结构化分析和补充分析的结论
- 连接泄漏：单 IP 占比 > 30% 或连接数 > 50
- 锁阻塞：锁等待链分析
- 慢查询：长时间 SQL 是否需要 kill
- 连接池：Sleep 占比 > 80% 建议调整
```

## 注意事项

- `address` 必须为 `ip:port` 格式
- `bk_cloud_id` 为整数，从拓扑结果中提取
- 拓扑查询失败则终止，不继续后续步骤
- 所有 processlist 调用结果必须重定向到文件，不在终端直接输出
