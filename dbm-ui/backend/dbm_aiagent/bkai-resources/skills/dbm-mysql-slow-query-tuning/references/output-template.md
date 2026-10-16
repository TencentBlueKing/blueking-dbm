## 慢查询分析：<cluster_domain>

采集时间：<start_time> ~ <end_time>

### 总结
Summary 的内容
```
  jq .summary $OUTPUT_DIR/slowlog_<cluster_domain>_analysis.json
```

---

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

