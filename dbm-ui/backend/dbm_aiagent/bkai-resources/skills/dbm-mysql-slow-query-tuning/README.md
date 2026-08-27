# mysql-slow-query-tuning

MySQL 慢查询分析与调优。

## 功能

1. **慢查询采集**：从 DBM 慢查询聚合接口拉取指定集群、指定时间范围内的 TOP N 慢查询（默认按 query_time_max 排序取 TOP 10）
2. **自动 EXPLAIN + 表结构采集**：对每条慢查询自动执行 `EXPLAIN` 和 `SHOW CREATE TABLE`，获取执行计划与索引信息
3. **逐条分析输出**：逐条输出完整的优化方案文档，每条 SQL 包含：
   - SQL 指纹与耗时/扫描行数等统计
   - `SHOW CREATE TABLE` 原始表结构
   - `EXPLAIN` 原始执行计划表格
   - 结合表结构和执行计划给出的具体优化建议（如缺失索引、全表扫描、索引选择不当等）
   - 所有条目输出完毕后追加总结：归纳共性问题、按严重程度排列优化优先级
4. **多集群类型支持**：适用于 tendbsingle / tendbha / tendbcluster，自动按集群类型选择默认查询角色
5. **多排序维度**：支持按 query_time_max、count_star、rows_examined_sum 等多种指标排序采集

## 工作流程

```
确认集群信息 → 确定查询角色 → 拉取慢查询列表
    → 提取慢查询数组 → batch-analyze.py 逐条获取 EXPLAIN + 表结构
    → 逐条按模板输出分析结果 → 追加总结
```

## 目录结构

```
mysql-slow-query-tuning/
├── SKILL.md                                # skill 主文件（流程定义）
├── README.md                               # 本文件
├── scripts/
│   └── batch-analyze.py                    # 串行执行 EXPLAIN + SHOW CREATE TABLE
└── references/
    ├── output-template.md                  # 输出格式模板（逐条 + 总结）
    └── slowlog-response-example.json       # 慢查询接口返回结构示例
```

## 使用的 MCP 接口

| 接口 | 用途 | 调用方 |
|------|------|--------|
| `mysql_slowlog_query_aggregated` | 获取慢查询聚合列表 | SKILL.md 步骤 3 |
| `mysql_query_explain_sql` | 执行 EXPLAIN | batch-analyze.py |
| `mysql_query_show_create_tables` | 获取表结构 | batch-analyze.py |

## 依赖

- `common-cluster-base-info`：由 AGENTS.md 在进入本 skill 前自动调用，提供 `cluster_domain` 和 `cluster_type`
