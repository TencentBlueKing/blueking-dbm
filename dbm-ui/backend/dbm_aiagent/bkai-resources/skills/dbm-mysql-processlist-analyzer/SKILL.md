---
name: dbm-mysql-processlist-analyzer
description: 分析 MySQL processlist 连接。当用户提到分析连接、查看 processlist、排查连接问题、检查谁在连数据库时触发。支持单实例和集群两种模式。
metadata: {"version":"1.0.6","space_id":"1d3d86fa67bef8c3","bk_skill_code":"dbm-mysql-processlist-analyzer","is_public":false,"bkai-dependencies":{"envs":[{"key":"DBM_MCPS","description":"dbm mcp server 地址列表","required":true,"default":"bkdbm-mcp-prod-mysql-query","secret":false},{"key":"OUTPUT_DIR","description":"skills 产物输出路径","required":false,"default":".storage/session","secret":false}]}}
---

# MySQL Processlist 分析

## 模式判断

- **集群模式**：用户提供集群域名（`cluster_domain`）
- **单实例模式**：用户提供 `ip:port`

## 集群模式

### 第一步：运行分析

```bash
python3 {SKILL_DIR}/scripts/run_analysis.py --cluster <cluster_domain> \
  --raw-query "<用户原始问题>" \
  -o $OUTPUT_DIR/analysis_result.tsv
```

脚本自动完成：拓扑解析 → 识别 MySQL/Proxy → 并行抓取 processlist → 提取 → 诊断 → 交叉验证 → 跨层关联（TenDBHA）。所有中间文件保留在 `$OUTPUT_DIR/`，进度输出到 stderr。

### 第二步：读取结果并呈现

读取 `$OUTPUT_DIR/analysis_result.tsv`，按"输出格式"章节的规则呈现。**禁止直接输出原始数据**。

结果文件说明：

| 文件 | 格式 | 内容 |
|------|------|------|
| `analysis_result.tsv` | TSV | 集群概览 + 各实例汇总（连接数、findings 数量） |
| `diag_<addr>.json` | JSON | MySQL 实例诊断详情（含原始 SQL，保留 JSON） |
| `diag_<addr>.tsv` | TSV | Proxy 实例诊断详情（无原始 SQL，紧凑格式） |
| `cv_<addr>.tsv` | TSV | 交叉验证数据（变量、状态、长事务数量） |
| `cross_layer.tsv` | TSV | 跨层关联 findings |

读取顺序：先读 `analysis_result.tsv` 获取全局概览，再按需读取有 findings 的实例 diag 文件和 cross_layer 文件。

### 第三步：等待用户反馈

**不要主动清理文件**。用户可能有后续问题需要访问中间数据。

追问时可基于"数据结构说明"中的字段定义编写 Python 代码分析 `$OUTPUT_DIR/pl_<ip>_<port>.json` 文件。也可用 `analyze_processlist.py` 的其他模式：

| 类型 | 说明 |
|------|------|
| `summary` | 概览 + Top 用户/IP/指纹/库 + 最长连接 + 锁等待 |
| `group_by_fingerprint` | SQL 指纹聚合（MySQL 独有） |
| `group_by_state` | 状态分布 |
| `group_by_user` | 用户聚合 |
| `group_by_client_host` | 来源 IP 聚合 |
| `group_by_db` | 库名聚合 |
| `group_by_destination_host` | 后端实例分布（Proxy 独有） |
| `lock_wait` | 锁等待检测 |
| `longest_top_5` | 最长运行查询 |
| `sample` | 活跃连接采样（最多 30 条） |

```bash
python3 {SKILL_DIR}/scripts/analyze_processlist.py $OUTPUT_DIR/pl_<ip>_<port>.json --type <type> \
  > $OUTPUT_DIR/detail_<type>_<ip>_<port>.json
```

每次追问产生的新结论要记录下来，纳入最终报告。

### 第四步：生成报告、上传、清理

**仅在用户明确表示没有其他问题时**执行。

**1. 生成报告**：将完整 markdown 报告写入 `$OUTPUT_DIR/report_<cluster>.md`，包括诊断发现、交叉验证、跨层关联、以及用户追问中产生的补充分析。

**2. 上传报告**（需要 `bkdbm-mcp-prod-ai-report` MCP 服务器）：

```bash
dbm-mcp-cli call bkdbm-mcp-prod-ai-report.ai_report_write_report \
  body_param='{"ai_agent": "mysql-processlist-analyzer", "format": "markdown", "bk_biz_id": <bk_biz_id>, "cluster_domain": "<cluster_domain>", "title": "<报告标题>", "summary": "<一句话摘要>", "content": "@$OUTPUT_DIR/report_<cluster>.md"}'
```

从返回的 `response_body.data.share_url` 提取分享链接并返回给用户。

**3. 清理**：

```bash
rm -f $OUTPUT_DIR/pl_raw_*.json $OUTPUT_DIR/pl_*.json $OUTPUT_DIR/diag_*.json $OUTPUT_DIR/diag_*.tsv $OUTPUT_DIR/trx_*.json $OUTPUT_DIR/vars_*.json $OUTPUT_DIR/status_*.json $OUTPUT_DIR/cross_layer.tsv $OUTPUT_DIR/cv_*.tsv $OUTPUT_DIR/analysis_result.tsv $OUTPUT_DIR/report_*.md $OUTPUT_DIR/detail_*.json
```

## 单实例模式

### 第一步：运行分析

```bash
# MySQL 实例
python3 {SKILL_DIR}/scripts/run_analysis.py --instance <ip:port> \
  --raw-query "<用户原始问题>" -o $OUTPUT_DIR/analysis_result.json

# Proxy 实例
python3 {SKILL_DIR}/scripts/run_analysis.py --instance <ip:port> --proxy \
  --raw-query "<用户原始问题>" -o $OUTPUT_DIR/analysis_result.json
```

`--bk-cloud-id` 未指定时默认 `0`。用户未说明实例类型时默认 MySQL。

### 第二步~第四步

同集群模式。单实例的结果结构：

```
{
  "instance": "<ip:port>",
  "bk_biz_id": 0,
  "result": { "address", "role", "source_type", "total", "active", "idle", "findings": [...] },
  "cross_verification": { ... }
}
```

## 数据结构说明

提取后的 `pl_<ip>_<port>.json` 是一个数组，每个元素是一条连接记录。

**MySQL processlist 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 连接 ID |
| `source_host` | string | 客户端来源 `ip:port`（经过 Proxy 时为 Proxy 的 IP） |
| `user` | string | 连接用户名 |
| `db` | string | 当前使用的数据库 |
| `command` | string | `Sleep` / `Query` / `Connect` / `Killed` / `Binlog Dump` 等 |
| `time` | int | 当前状态持续秒数 |
| `state` | string | `login` / `Waiting for table metadata lock` / `Sending data` 等 |
| `info` | string\|null | 正在执行的 SQL 原文 |
| `fingerprint` | string | SQL 指纹（参数化后的 SQL） |
| `fingerprint_md5` | string | SQL 指纹的 MD5 |
| `tables` | string | 涉及的表名 |
| `query_len` | int | 查询长度 |

**Proxy processlist 字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 连接 ID |
| `source_host` | string | **真实客户端** `ip:port` |
| `user` | string | 连接用户名 |
| `db` | string | 当前数据库 |
| `destination_host` | string | 后端 MySQL 实例 `ip:port` |
| `state` | string | `CON_STATE_READ_QUERY`（空闲）/ `CON_STATE_READ_QUERY_RESULT` / `CON_STATE_READ_HANDSHAKE` / `CON_STATE_READ_AUTH_RESULT` 等 |
| `time` | int | 当前状态持续秒数 |

> **规则**：对原始 processlist 数据做自主分析时，**禁止使用 `cat` / `head` / `tail` 查看 JSON 文件内容**。应基于上述字段说明直接编写 Python 代码读取和分析。

## 输出格式

读取分析结果 JSON，按以下规则呈现。禁止直接输出原始 JSON。

### diagnose findings 呈现规则

- `findings` 为空 → 一句话："实例 \<address\>（\<角色\>）连接状况正常（总连接 N，活跃 N）"
- `findings` 非空 → 按 severity 排列：
  - severity 标签： high /  medium /  low
  - `title`（脚本已生成中文标题）
  - `detail`（如有）
  - `pattern_analysis`（如有）
  - `evidence` 中的连接明细（表格展示，`time_human` 已提供人类可读时长）
  - `idle_bloat` 的 `by_user` 注意 `pattern`：`bimodal` → "双峰模式"，`leak` → "泄漏模式"
  - `actions`（如有）→ **必须展示**，标题用"辅助定位 SQL"，**原样输出** `actions` 数组中的每条 SQL（脚本已生成好），用 sql 代码块展示，不可省略

### cross_verification 呈现规则

在该实例 findings 之后展示：
- `trx_long_running` 为空 → "无未提交事务，确认为连接池泄漏"
- `trx_long_running` 非空 → 展示事务详情
- `variables` + `status` → 展示连接容量判断：
  - `Threads_connected / max_connections > 80%` → 连接即将耗尽
  - `Threads_running` 低但 `Threads_connected` 高 → 连接池泄漏
  - `Connection_errors_max_connections > 0` → 已发生连接拒绝

### cross_layer findings 呈现规则

跨层关联结果作为报告中 **最重要的章节** 展示，直接回答"谁造成的问题"：

- `auth_pressure_traced` → MySQL 鉴权连接来自哪个 Proxy → 真实客户端 IP
- `idle_traced` → MySQL 长 Sleep 用户 → 经 Proxy 追溯的真实客户端 IP（这是最有价值的输出）
- `stale_verified` → Proxy 滞留连接在 MySQL 侧的真实状态（泄漏 / 幽灵 / 慢查询）
- `connection_consistency` → MySQL 与 Proxy 连接数差异

### 输出示例

```
## 集群 <domain> 连接诊断

### Master <address>
总连接: N | 活跃: N | 空闲: N

 发现 N 个长时间 Sleep 连接...
   **辅助定位 SQL**：（原样输出 actions 数组中的每条 SQL）

 空闲连接占比过高...
   **辅助定位 SQL**：（原样输出 actions 数组中的每条 SQL）

#### 交叉验证
**未提交事务**：无 → 确认连接池泄漏
**连接容量**：Threads_connected=7423 (82.5%) ...

### Slave <address>
连接状况正常（总连接 6，活跃 1）

### 跨层关联分析

**连接泄漏追溯**：
| 用户 | MySQL 空闲连接 | 真实客户端 IP | 结论 |
| bkapp-ai-zd--bqf | 293 | 192.168.242.123(293) | 单机泄漏 |
→ 运维操作：联系 192.168.242.123 排查连接池配置

**Proxy 滞留连接验证**：
7 个 Proxy 连接泄漏（MySQL 侧已空闲但 Proxy 未释放）
```

### 综合建议呈现规则

**必须**在报告末尾给出综合建议，结合全部诊断数据进行推理。建议按优先级排列，每条包含：

1. **紧急程度**（紧急 / 重要 / 建议 / 关注）
2. **问题本质**：不是复述 finding，而是综合多个 finding 得出结论（例：大量 Sleep + trx_long_running 为空 + Threads_running 低 → 连接池泄漏占满容量）
3. **操作建议**：具体可执行的操作（SQL 命令、配置调整、联系哪个 IP 的应用方排查什么问题）
4. **预期效果**：执行后预计改善的量化指标

推理示例：
- `idle_bloat`(leak) + `trx_long_running` 为空 → 连接池泄漏，建议清理并联系应用方
- `idle_traced` 定位到单机 IP → 建议联系该 IP 排查连接池 `maxIdle`/`maxLifetime`
- `Max_used_connections >= max_connections` → 已发生连接拒绝，需紧急扩容或清理
- `wait_timeout` 远小于实际 Sleep 时长 → 应用在保活连接，调低 timeout 无效，需应用侧修复
- `stale_verified` 有 leak → Proxy 层连接泄漏，建议检查 Proxy 版本

### Kill 连接

当诊断发现需要 kill 的问题连接时（如长时间 Sleep 泄漏连接、阻塞其他会话的长事务等），告知用户可以通过 `mysql-kill-connection` skill 执行 kill 操作，需提供目标实例的 `address`（ip:port）和连接 `id`。

## 注意事项

- `address` 必须为 `ip:port` 格式
- **所有产生 JSON 数据的命令必须重定向到文件**，禁止直接在终端输出大量 JSON
- **禁止 `cat` / `head` / `tail` 查看 processlist JSON**，基于数据结构说明编写 Python 代码分析
- **TenDBHA 集群的跨层关联**是报告中最有价值的部分——它把"MySQL 有很多 Sleep 连接"转化为"哪个真实客户端 IP 泄漏了连接"
- **不要推测账号用途**，只描述数据中看到的现象（连接数、模式、时长等），不要编造账号是干什么的
- **TenDBHA Slave 角色区分**：`backend_slave_standby`（is_stand_by=True）是高可用备机，不应有复杂查询；`backend_slave_readonly`（is_stand_by=False）是读分流节点，承接业务读流量
- **TenDBCluster 接入层区分**：`spider_master` 是正常读写路径，请求发送到 `remote_master`；`spider_slave` 是读分流路径，请求发送到 `remote_slave`
- **读分流节点容忍度更高**：`backend_slave_readonly` 和 `spider_slave` 对慢 SQL 的容忍度高于主路径，分析时应区别对待
- **TenDBCluster 默认只分析代表分片**：脚本默认只取第一个分片对（1 个 remote_master + 1 个 remote_slave）做代表，接入层全量分析。告知用户此行为，如需分析全部 remote 可加 `--all-remotes`