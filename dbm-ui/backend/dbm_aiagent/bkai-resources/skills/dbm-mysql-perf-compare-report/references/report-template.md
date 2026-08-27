# 性能对比分析报告

> 生成时间：{generated_at}
> 分析时段：{analysis_start} ~ {analysis_end}
> 慢查询基准：{baseline_date} 全天
> 负载基准时段：{metrics_baseline_start} ~ {metrics_baseline_end}

---

## 一、新增慢查询（完全匹配模式）

| 集群 | 本次 digest 数 | 基准 digest 数 | 新增 |
|------|---:|---:|---:|
| {cluster} | {cur_cnt} | {base_cnt} | {new_cnt} |

---

## 二、新增慢查询明细

### {cluster}（新增 {N} 条）

**[{SQL_TYPE}] {n} 条**

| digest | db | SQL 指纹 | cnt | qt_max | rows_ex |
|--------|----|---------|----:|-------:|-------:|
| {digest} | {db} | `{sql_fingerprint}` | {cnt} | {qt_max}s | {rows_ex} |

---

## 三、CPU 对比（{metrics_baseline_start} ~ {metrics_baseline_end}）

| 集群 | 角色 | 本次 avg/max | 基准 avg/max | 变化 |
|------|------|-------------|-------------|------|
| {cluster} | Proxy/Spider | {t_avg}% / {t_max}% | {y_avg}% / {y_max}% | {flag} {delta}% |
| | Master | ... | ... | ... |
| | Slave/Remote | ... | ... | ... |

---

## 四、QPS 对比（{metrics_baseline_start} ~ {metrics_baseline_end}）

| 集群 | 角色 | 本次 avg/max | 基准 avg/max | 变化 |
|------|------|-------------|-------------|------|
| {cluster} | Proxy/Spider | {t_avg} / {t_max} | {y_avg} / {y_max} | {flag} {pct}% |
| | Master | ... | ... | ... |

---

## 五、综合结论

| 集群 | 结论 |
|------|------|
| ⚠️ {cluster} | {issue_desc} |
| ✅ {cluster} | 无异常 |
