# 告警类型: 慢查询数量过多 (slow_queries)

## 告警解释

MySQL 实例的慢查询数量指标 (`mysql_global_status_slow_queries`) 超过阈值（通常 ≥ 3000），说明实例中大量 SQL 执行时间超过了 `long_query_time` 设定值。可能导致：
- 数据库整体性能下降
- 应用端请求超时增多
- 磁盘 IO 压力增大（慢查询往往伴随大量行扫描）

常见原因：
- 缺少合适索引导致全表扫描
- 表数据量增长，原有索引效率下降
- 突发大批量数据操作（如批量导入/更新）
- SQL 写法不佳，产生笛卡尔积或不必要的子查询
- 锁等待/锁争用导致 SQL 执行变慢

## 分析步骤


# MySQL 慢查询分析

## 职责说明

本 skill 负责采集慢查询数据、执行 EXPLAIN，并基于结果给出优化建议。

## 工作流程

### 1. 确认集群信息

- 集群域名 cluster_domain
- 慢查询时间范围，当用户指定了时间范围，就不要擅自扩大或者缩小时间范围

### 2. 确定 instance_role

如果用户明确指定了查询角色，使用用户指定的值。否则按集群类型使用默认值：

| cluster_type | 默认 instance_role |
|---|---|
| tendbha | backend_master |
| tendbcluster | spider_master |
| tendbsingle | orphan |


### 3. 获取慢查询列表

默认按 query_time 排序取 top10

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-slowlog.mysql_slowlog_query_aggregated \
  body_param='{"cluster_domain": "<cluster_domain>", "instance_role": "<instance_role>", "start_time": "<开始时间>", "end_time": "<结束时间>", "metric_name": "query_time_max", "limit": 10}' \
  > $OUTPUT_DIR/slowlog_<cluster_domain>.json
```

metric_name 还有其他可选项：count_star, rows_examined_sum, rows_examined_max, query_time_sum, query_time_max, rows_sent_max, rows_sent_sum .

返回结构参考：`./references/alarm_slow_queries/references/slowlog-response-example.json`

### 4. 提取慢查询数组

```bash
jq '.response_body.data.slow_logs' $OUTPUT_DIR/slowlog_<cluster_domain>.json > $OUTPUT_DIR/slowlog_<cluster_domain>_body.json
```

### 5. 获取表结构和执行计划

batch-analyze.py 脚本会循环调用 dbm-mcp-cli 来对每条慢查询，获取 table schema  和 explain 执行计划:

```bash
./references/alarm_slow_queries/scripts/batch-analyze.py <cluster_domain>
```

输入：`$OUTPUT_DIR/slowlog_<cluster_domain>_body.json`（慢查询数组）
输出：
- `$OUTPUT_DIR/slowlog_<cluster_domain>_explain.json` — EXPLAIN 结果数组，每项含 `query_digest_md5`
- `$OUTPUT_DIR/slowlog_<cluster_domain>_schema.json` — 表结构结果数组，每项含 `query_digest_md5`

### 6. 逐条分析并输出

**硬约束：必须严格按模板逐条输出，不得合并、汇总或省略任何条目。每条 SQL 必须包含完整的 EXPLAIN 原始表格，不得跳过。**

数据收集完成，逐条处理（i 从 0 开始）。每轮只读取一条数据：

```bash
# 读取第 i 条慢查询的 sql 统计信息
jq ".[$i]" $OUTPUT_DIR/slowlog_<cluster_domain>_body.json

# 读取对应的 explain 结果
jq ".[$i]" $OUTPUT_DIR/slowlog_<cluster_domain>_explain.json

# 读取对应的 table schema 表结构信息
jq ".[$i]" $OUTPUT_DIR/slowlog_<cluster_domain>_schema.json
```

严格按 `./references/alarm_slow_queries/references/output-template.md` 中的模板输出，不得改变结构。输出完一条后再处理下一条，直到所有条目处理完毕，最后追加总结段。
