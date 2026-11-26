# 过期数据清理

analysis 定期物理删除 `t_dbm_metadata` 与 `t_dbha_status` 中长期不再更新的行，避免两张表无限增长。本文是运维手册；
工作原理、保障机制和设计取舍见 [设计：analysis 过期数据清理](data-retention-design.md)。

## 1. 规则

- 判定只看 `updated_at`：`updated_at < now - 保留期` 的行被删除，两张表的默认保留期都是 `336h`（14 天）。
- 不改表结构、不加索引、不改任何读写路径。被删的行不参与检测，实例恢复后会自动重建，理由见
  [设计文档 3.3 节](data-retention-design.md#33-业务正确性)。
- 唯一可见的行为变化：只剩过期行的业务不再出现在 analysis 的业务扫描列表中。

## 2. 执行方式

- 每套部署只有一个 analysis 实例执行，etcd 选举名 `gc-dbha-data-retention`。
- 两张表独立调度。当选后 1–10 分钟内首次执行；之后每 `interval`（默认 6h）发起一遍遍历，每个窗口读
  `scanWindowRows`（默认 2 万）行，窗口之间间隔 `drainInterval`（默认 5m），过期行按主键分批删除（每批 `batchSize`，默认 500）。
- 窗口、游标与删除复核的细节见 [设计文档第 2 节](data-retention-design.md#2-工作原理)。

清理始终让路于故障诊断，出现以下情况会结束本次执行，`drainInterval` 后重试：

| 情况 | 说明 |
| --- | --- |
| 有切换进行中 | `t_db_switching_snapshot_log` 中存在 `switchTimeout` 内开始、状态为 `doing` 的记录 |
| 删除变慢 | 上一批删除耗时超过 `slowDeleteThreshold`（默认 1s） |
| 超出时间预算 | 单表单次执行超过 `roundTimeBudget`（默认 60s） |
| 语句超时或出错 | 计入停滞判定，见第 5 节 |

写入源健康检查：表中在 `metadataHealthWindow` / `statusHealthWindow`（默认 10m / 5m）内没有任何更新时，
说明同步或上报已中断，本次跳过该表，`interval` 后再检查。

## 3. 配置

配置位于 `analysis.yaml` 的 `workflow.retention`。部署模板和 `dbha-v2.server.rc.example` 已带下列默认值；未包含 `retention` 的旧配置文件仍使用代码默认值，无需修改。

```yaml
workflow:
  retention:
    enabled: true
    metadataRetention: 336h
    statusRetention: 336h
    interval: 6h
    drainInterval: 5m
    scanWindowRows: 20000
    maxRowsPerRound: 10000
    batchSize: 500
    batchSleep: 200ms
    scanTimeout: 10s
    healthCheckTimeout: 10s
    deleteTimeout: 10s
    slowDeleteThreshold: 1s
    roundTimeBudget: 60s
    metadataHealthWindow: 10m
    statusHealthWindow: 5m
    stallAlertAfter: 24h
```

非法值打印告警并回落到安全值，不会阻止 analysis 启动：

- 保留期不得小于 24h，也不得小于对应读窗口（`readDbMetaOffsetDuration`、`readDbMetricOffsetDuration` 的绝对值）。
- `metadataHealthWindow` 不小于 `max(10m, 3 × updateDbmCacheInterval)`；`statusHealthWindow` 不小于
  `max(5m, 3 × |readDbMetricOffsetDuration|)`。
- `slowDeleteThreshold < deleteTimeout`，`scanTimeout < roundTimeBudget`。
- `batchSize ≤ maxRowsPerRound ≤ scanWindowRows`，且 `1000 ≤ scanWindowRows ≤ 100000`。

**配置不支持热加载。** analysis 收到 `SIGHUP`（含 `reload` 子命令）只打印日志，修改 `enabled` 等配置需要重启
analysis 才生效。

## 4. 上线与运维

清理默认开启，升级后 1–10 分钟内开始执行。`dbha-admin migrate` 必须先于开启 retention 的 analysis。迁移未完成时，
先把 `workflow.retention.enabled` 设为 `false` 再启动 analysis。以下预检须在**升级 analysis 之前**完成；需要推迟清理时，
升级前在 `analysis.yaml` 中写入 `workflow.retention.enabled: false`，准备好后改回并重启 analysis。

预检（只读）：

```sql
-- 两表规模与待清理行数
SELECT COUNT(*) AS total, SUM(updated_at < NOW() - INTERVAL 14 DAY) AS stale FROM t_dbha_status;
SELECT COUNT(*) AS total, SUM(updated_at < NOW() - INTERVAL 14 DAY) AS stale FROM t_dbm_metadata;

-- 平均行长：scanWindowRows × AVG_ROW_LENGTH 建议不超过约 64MB，超过时调小 scanWindowRows
SELECT TABLE_NAME, TABLE_ROWS, AVG_ROW_LENGTH FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'dbha_data' AND TABLE_NAME IN ('t_dbha_status', 't_dbm_metadata');

-- 版本：MAX_EXECUTION_TIME 需要 5.7.8 及以上，低版本仅依赖客户端超时
SELECT VERSION();

-- analysis 存储账号需要两表的 DELETE 权限
SHOW GRANTS;

-- 其他直接读取 dbha_data 的账号，需与使用方确认不依赖 14 天以前的历史行
SELECT user, host FROM mysql.db WHERE db = 'dbha_data' AND Select_priv = 'Y';
SELECT user, host, table_name FROM mysql.tables_priv WHERE db = 'dbha_data';
```

同时记录从库复制延迟基线，用于上线后对比。

- **紧急停止**：改为 `enabled: false` 并重启 analysis。
- **admin migrate**：执行前先按上一条关闭清理，或在 migrate 维护窗口内一并停止 analysis。
- **回滚**：回退 analysis 版本即停止清理，不会删除 `idx_updated_at`；旧版本可以留着这个索引读写。已删除的行会随同步与上报自动重建。
- **表空间**：`DELETE` 不回收磁盘空间，需要时另行安排 `OPTIMIZE TABLE`。

## 5. 观测

指标与告警见 [analysis 指标](../observability/analysis-metrics.md) 的"数据清理"部分。语句结果按以下方式归类：

| 类别 | 例子 | 处理 | 是否计入停滞 |
| --- | --- | --- | --- |
| 正常让路 | 有切换进行中；写入源没有最近更新 | 推迟或跳过 | 否 |
| 锁冲突 | 删除遇到死锁（1213）或锁等待超时（1205） | 跳过该批，视为已处理 | 计入 `deadlock` |
| 超时 | 触发 `MAX_EXECUTION_TIME`（3024）或客户端超时 | 结束本次执行，游标停在最后已处理处 | 是 |
| 其他错误 | 快照表不存在、没有 DELETE 权限（1142）、连接错误 | 结束本次执行 | 是 |

停滞：连续 `stallAlertAfter`（默认 24h）没有删除任何行，且期间存在待删行、超时或其他错误时，
`retention_stalled` 置为 1。没有待删行的执行视为正常推进。

## 6. 已知限制

见 [设计文档 3.4 节](data-retention-design.md#34-保障的边界已知限制)。运维上需要特别注意的两点：receiver 配置多个写入库时只清理
analysis 连接的库；执行计划退化时表现为停滞告警，需要人工排查。

---

返回：[文档入口](../README.md)
