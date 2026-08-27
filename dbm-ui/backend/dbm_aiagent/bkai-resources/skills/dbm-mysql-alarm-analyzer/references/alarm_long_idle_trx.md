# 告警类型: 长空闲事务未关闭

## 告警解释

MySQL 长空闲事务告警（`innodb_trx_idle_time_max` 指标）表示某个连接开启了事务后，长时间处于空闲状态（超过 1 小时未执行任何操作）。

**风险**：
- 长时间持有行锁或元数据锁，阻塞其他事务和 DDL 操作
- 阻止 InnoDB purge 线程回收 undo log，导致 undo 膨胀
- 可能影响 DB 例行全备操作（备份需要获取一致性快照）
- 极端情况下导致磁盘空间不足

**建议处理**：业务侧应尽快 `COMMIT` / `ROLLBACK` 该事务，或关闭对应连接。

## 分析步骤

### Step 1: 查看长事务详情

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_trx_long_running \
  body_param='{"address": "<ip:port>", "bk_cloud_id⁠":<云区域id, 默认 0>}' \
  --raw-query "<用户原始问题>"
```

参数提取：
- `address`: 从告警维度 `instance_host` + `instance_port` 提取，格式为 `ip:port`

**重点关注**：
- 事务已持续的时间（`trx_idle_time` 或类似字段）
- 事务来源连接的 `source_host`（对于 tendbha 集群，这可能是 proxy IP 而非真实客户端 IP）
- 事务关联的 SQL 语句
- 连接 `id`（后续步骤关联用）

### Step 2: 获取真实客户端 IP（仅 tendbha 集群需要）

> 如果集群类型**不是 tendbha**，跳过此步骤。

tendbha 集群中，Step 1 看到的 `source_host` 是 mysql-proxy 的 IP，需要进一步追溯真实客户端来源。

#### Step 2a: 查询集群拓扑，获取 proxy 的 ip:port

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_mysql_cluster_topo \
  body_param='{"cluster_domain": "<cluster_domain>"}' \
  --raw-query "<用户原始问题>"
```

从拓扑结果中找到 Step 1 返回的 `source_host`（proxy IP）对应的 proxy 实例完整地址 `proxy_ip:proxy_port`，还有云区域 bk_cloud_id 字段。

#### Step 2b: 查询 proxy processlist，关联真实客户端

输出结果可能很大，重定向到文件:
```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_show_proxy_processlist \
  body_param='{"address": "<proxy_ip:proxy_port>", "bk_cloud_id": <bk_cloud_id>}' \
  --raw-query "<用户原始问题>" > $OUTPUT_DIR/pl_raw_<ip>_<port>.json
```

**关联方法**：
- proxy processlist 返回的每条连接包含 `id` 和 `source_host`
- 通过 `id` 与 Step 1 中长事务的连接 `id` 进行关联
- 匹配到的记录中的 `source_host` 即为真实客户端 IP
- 当文件内容超过工具输出上下文阈值时，可以尝试 `head -c 1000 <file>` 来读取前 1000 个字符来预览一下。

## 报告输出格式

### 长空闲事务详情

| 字段 | 值 |
|------|-----|
| 事务持续时间 | xx 秒 (约 xx 小时 xx 分钟) |
| 连接 ID | xx |
| 来源地址 | xx（如为 proxy IP 则标注） |
| 真实客户端 IP | xx（仅 tendbha，通过 proxy processlist 关联） |
| 关联 SQL | xx |

（如有多个长事务，以表格形式逐行列出）

### 综合判断

根据以上结果分析：
- 长事务已持续的时间及风险等级
- 事务来源（哪个客户端 IP / 应用）
- 建议业务侧尽快 COMMIT / ROLLBACK 或关闭连接
- 如事务持续时间过长（>数小时），提示可能影响全备和 undo 空间
