---
name: dbm-mysql-slow-query-tuning
description: MySQL 慢查询分析与调优。当用户提到"慢查询调优"、"慢查询优化"、"慢 SQL 分析"、"explain 分析"时触发。适用于 DBM 平台管理的 MySQL 集群（tendbsingle / tendbha / tendbcluster）。
metadata: {"version":"1.0.6","space_id":"1d3d86fa67bef8c3","bk_skill_code":"dbm-mysql-slow-query-tuning","is_public":false,"bkai-dependencies":{"envs":[{"key":"DBM_MCPS","description":"dbm mcp server 地址列表","required":true,"default":"bkdbm-mcp-prod-mysql-query bkdbm-mcp-prod-mysql-slowlog bkdbm-mcp-prod-ai-report bkdbm-mcp-prod-dbmeta-query","secret":false},{"key":"OUTPUT_DIR","description":"skills 产物输出路径","required":false,"default":".storage/session","secret":false}]}}
---

# MySQL 慢查询分析

## 职责说明

本 skill 负责采集慢查询数据、执行 EXPLAIN，并基于结果给出优化建议。

- 打印 $OUTPUT_DIR 确认环境变量，如果有值则不用额外设置，如果为空则设置为 当前工作区目录。

## 工作流程

### 1. 确认集群信息

- 集群域名 cluster_domain
- 慢查询时间范围，当用户指定了时间范围，就不要擅自扩大或者缩小时间范围
- 调用 mcp mysql_query_mysql_cluster_topo 获取集群 拓扑,ip,version 等信息

```
dbm-mcp-cli call bkdbm-mcp-prod-mysql-query.mysql_query_mysql_cluster_topo \
  body_param='{"cluster_domain": "<cluster_domain>"}' 
```

### 2. 确定 instance_role

如果用户明确指定了查询角色，使用用户指定的值。否则按集群类型使用默认值：

| cluster_type | 默认 instance_role |
|---|---|
| tendbha | backend_master |
| tendbcluster | spider_master |
| tendbsingle | orphan |

### 3. 获取慢查询列表

默认按 query_time_max 排序取 top10, **注意使用 --output-file 输出到文件**，因为返回结果很大避免占用上下文.

```bash
dbm-mcp-cli call bkdbm-mcp-prod-mysql-slowlog.mysql_slowlog_query_aggregated \
  body_param='{"cluster_domain": "<cluster_domain>", "instance_role": "<instance_role>", "start_time": "<开始时间>", "end_time": "<结束时间>", "metric_name": "query_time_max", "limit": 10}' \
  --output-file $OUTPUT_DIR/slowlog_<cluster_domain>.json
```

metric_name 还有其他可选项：count_star, rows_examined_sum, rows_examined_max, query_time_sum, query_time_max, rows_sent_max, rows_sent_sum .

返回结构参考：`./skills/mysql-slow-query-tuning/references/slowlog-response-example.json`

### 4. 提取慢查询数组

```bash
jq '.response_body.data.slow_logs' $OUTPUT_DIR/slowlog_<cluster_domain>.json > $OUTPUT_DIR/slowlog_<cluster_domain>_body.json
```

### 5. 获取表结构和执行计划

batch-analyze.py 脚本会循环调用 dbm-mcp-cli 来对每条慢查询，获取 table schema  和 explain 执行计划:

```bash
# exec workdir variable should be set to your agent workspace
python scripts/batch-analyze.py <cluster_domain>
```

输入：`$OUTPUT_DIR/slowlog_<cluster_domain>_body.json`（慢查询数组）
输出：
- `$OUTPUT_DIR/slowlog_<cluster_domain>_explain.json` — EXPLAIN 结果 map（key 为 `query_digest_md5`）
- `$OUTPUT_DIR/slowlog_<cluster_domain>_schema.json` — 表结构结果 map（key 为 `query_digest_md5`）

### 6. AI 逐条分析

数据收集完成后，逐条分析每条慢查询。每轮读取一条数据的 body、explain、schema，然后输出结构化的分析结果。

- 某些异常情况导致 schema/explain 为空或者有错误，可以基于你自己的知识进行简单判断，不要当失败处理

```bash
# 读取第 i 条慢查询的 sql 统计信息，获取其 query_digest_md5
jq ".[$i]" $OUTPUT_DIR/slowlog_<cluster_domain>_body.json

# 用 query_digest_md5 作为 key 读取对应的 explain 结果
jq ".[\"<query_digest_md5>\"]" $OUTPUT_DIR/slowlog_<cluster_domain>_explain.json

# 用 query_digest_md5 作为 key 读取对应的 table schema 表结构信息
jq ".[\"<query_digest_md5>\"]" $OUTPUT_DIR/slowlog_<cluster_domain>_schema.json
```

对每条 SQL 输出以下结构化分析（JSON 格式），分析完所有条目后，将**完整结果对象**写入 `$OUTPUT_DIR/slowlog_<cluster_domain>_analysis.json`：

```json
{
  "summary": {
    "most_urgent": "最紧急需要处理的问题描述（通常是按时间排序第一条出现的高风险慢查询）",
    "root_cause_summary": "综合根因归纳（如：某大事务阻塞全局、索引缺失、热点表锁争用等）",
    "key_findings": [
      "发现1：简要关键结论",
      "发现2：...",
      "发现3：..."
    ],
    "action_priority": "建议处理优先级说明（先解决什么、后解决什么）"
  },
  "queries": {
    "<digest_md5>": {
      "problem": "简要描述该 SQL 的性能问题（如：全表扫描、索引失效、大批量删除等）",
      "root_cause": "根因分析（如：WHERE 条件无法命中索引、扫描行数过大、锁争用等）",
      "suggestions": [
        "建议1：具体可操作的优化措施，需要简单明了",
        "建议2：...",
        "建议3：..."
      ],
      "risk_level": "high|medium|low"
    }
  }
}
```

> `queries` 是以 `query_digest_md5` 为 key 的对象（dict），方便后续用 jq 按 md5 直接检索。

**summary 字段说明**：
- `most_urgent`: 重点关注按时间最早出现的高风险查询，它往往是引发后续问题的根源
- `root_cause_summary`: 从全局视角归纳根因，多条 SQL 可能有相同根因（如大事务阻塞）
- `key_findings`: 3-5 条关键发现
- `action_priority`: 建议处理顺序

**分析要点**：
- 结合 EXPLAIN 的 type（ALL/index/range/ref 等）、key（是否为 NULL）、rows（扫描行数）
- 重点分析 **离 start_time 最近的慢查询**，重点分析关注它是否是源头。考虑谁最可能是根因，谁是被影响的
- 对比表结构中的已有索引，判断是否有索引缺失或索引选择不优
- 考虑 query_time_max、count_star、rows_examined_max 的综合影响
- 若多条 SQL 操作同一张表，注意分析是否存在锁争用问题
- risk_level: high = 严重影响性能需立即优化; medium = 有优化空间; low = 影响较小

### 7. 输出报告结果

报告有两种结果格式 markdown / html，统一使用 generate-report.py 生成。除非用户明确指定了 html 格式，否则默认 markdown 格式返回。

输入（由前面步骤生成）：
- `$OUTPUT_DIR/slowlog_<cluster_domain>_body.json` — 慢查询数组
- `$OUTPUT_DIR/slowlog_<cluster_domain>_explain.json` — EXPLAIN 结果 map（key 为 query_digest_md5）
- `$OUTPUT_DIR/slowlog_<cluster_domain>_schema.json` — 表结构结果 map（key 为 query_digest_md5）
- `$OUTPUT_DIR/slowlog_<cluster_domain>_analysis.json` — AI 分析结果 `{"summary": {...}, "queries": {<digest_md5>: {...}}}`

`--format` 可选 `markdown`（默认）或 `html`：

```bash
# markdown 报告（默认）
python scripts/generate-report.py <cluster_domain> \
  --start-time "<开始时间>" --end-time "<结束时间>"

# html 报告
python scripts/generate-report.py <cluster_domain> --format html \
  --start-time "<开始时间>" --end-time "<结束时间>"
```

输出：
- markdown：`$OUTPUT_DIR/slowlog_<cluster_domain>_report.md`
- html：`$OUTPUT_DIR/slowlog_<cluster_domain>_report.html`（可交互式 HTML 报告）


### 8. 输出总结

在 chat 中简要输出总结：
- 共分析 N 条慢查询,严重/警告/正常数量分布
- AI 分析慢查询结果总结：
  ```
  jq .summary $OUTPUT_DIR/slowlog_<cluster_domain>_analysis.json
  ```
  summary 展示了最紧急问题、综合根因、关键发现、处理优先级。
- 最后，调用 MCP 将 HTML 报告写入报告中心：(如果 content 字段是 @开头的文件路径，需要使用 dbm-mcp-cli 来调用，它支持以文件传参路径)

```bash
dbm-mcp-cli call bkdbm-mcp-prod-ai-report.ai_report_write_report \
  body_param='{"ai_agent": "mysql-slow-query-tuning", "cluster_domain": "<cluster_domain>", "title": "慢查询分析报告 - <cluster_domain>", "summary": "<报告摘要>", "content": "@<report_full_path>", "format": "<markdown or html>", "bk_biz_id":<appid or bk_biz_id>}'

# then, remove file: <report_full_path>
```
调用成功后返回报告访问地址给用户，最后提示 "AI 分析结果，执行优化时请咨询 DBA 的建议"。