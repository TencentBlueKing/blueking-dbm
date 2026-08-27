## 慢查询分析：<cluster_domain>

采集时间：<start_time> ~ <end_time>

### SQL #<i+1> (<query_digest_md5>)

用户名: user@host (出现次数: <count_star>)

| 查询耗时 | 扫描行数 | 总扫描行数 | 返回行数 | 库表名 | 首次时间 |
|---------|---------|---------|---------|--------|----------|
| query_time_max | rows_examined_max | rows_examined_sum | rows_sent_max | table_names | time_window_min |


**SQL 指纹**: 
```sql
<query_digest_text 字段，不得省略>
```


**表结构**：
```sql
<SHOW CREATE TABLE 原始输出，如果有多个表，空行后在这同一个代码块输出>
```


**EXPLAIN**：
| select_type | type | key | rows | filtered | Extra |
|---|---|---|---|---|---|
| <必须填写 EXPLAIN 原始数据，不得省略> |


**优化建议**：
- <结合表结构和 EXPLAIN 结果给出具体优化建议，如缺失索引、索引选择不当等>
- 控制字数，给最直接的问题和建议操作

---

（以上模板对每条 SQL 重复，直到所有条目输出完毕）

## 总结

- 共分析 N 条慢查询，尤其要重点分析 **离 start_time 最近的慢查询**，重点分析关注它是否是源头
- 主要问题：<归纳共性问题，如索引缺失、全表扫描等>
- 优先级建议：<按影响范围和严重程度排列优化顺序>
- 最后提示 "AI 分析结果，执行优化时请咨询 DBA 的建议"
