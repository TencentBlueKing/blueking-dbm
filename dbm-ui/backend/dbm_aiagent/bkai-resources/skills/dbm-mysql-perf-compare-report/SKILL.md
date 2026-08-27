---
name: dbm-mysql-perf-compare-report
description: "MySQL 集群性能对比分析报告：对比指定时间区间内的慢查询新增（全匹配模式）、CPU、QPS 变化，支持多集群批量，输出结构化分析报告。"
metadata: {"version":"1.0.5","space_id":"1d3d86fa67bef8c3","bk_skill_code":"dbm-mysql-perf-compare-report","is_public":false,"bkai-dependencies":{"envs":[{"key":"DBM_MCPS","description":"dbm mcp server 地址列表","required":true,"default":"bkdbm-mcp-prod-mysql-metrics bkdbm-mcp-prod-mysql-query bkdbm-mcp-prod-mysql-slowlog","secret":false},{"key":"OUTPUT_DIR","description":"skills 产物输出路径","required":false,"default":".storage/session","secret":false}]}}
---

# DBM 性能对比分析报告

针对业务维护/上线后的性能健康检查。全量对比慢查询（完全匹配模式，不截断 top），同时对比 proxy 和 remote(master/slave) 各角色的 CPU、QPS 波动。

## 输入参数

用户需提供：

- **cluster_domains**：集群域名列表（一行一个，或逗号分隔）
- **analysis_start**：本次分析开始时间
- **analysis_end**：本次分析结束时间
- **slowlog_baseline_date**：慢查询基准日期
- **metrics_baseline_start**：负载对比基准开始时间
- **metrics_baseline_end**：负载对比基准结束时间

### 时间格式规则

- 支持三种格式：`YYYY-MM-DD HH:MM:SS`、`YYYY-MM-DD HH:MM`、`YYYY-MM-DD`
- **只填日期（无时分秒）= 整天**：自动补全为 `00:00:00` ~ `23:59:59`
- `slowlog_baseline_date` 始终取整天，只需填日期即可

### 参数缺失处理规则

缺少任意参数时，**必须停止执行并提示用户补全，不得自行推断或复用上次的值**：

| 参数 | 若未提供则询问 |
|------|--------------|
| cluster_domains | 必须提供 |
| analysis_start/end | 询问「分析时间区间」|
| slowlog_baseline_date | 询问「慢查询基准日期（通常为昨天）」|
| metrics_baseline_start/end | 询问「负载对比基准时段」|

## 工作流程

### Step 0：获取集群拓扑

调用 `fetch_topo.py` 并发获取所有集群的拓扑信息：

```bash
python3 scripts/fetch_topo.py "<domain1>,<domain2>,..."
```

输出 `$OUTPUT_DIR/pcr_topo_all.json`，包含每个集群的 `cluster_type` 和角色映射。

角色映射规则：

| cluster_type | 慢查询 instance_role | proxy 角色 | master 角色 | remote/slave 角色 |
|---|---|---|---|---|
| tendbha | backend_master | proxy | backend_master | backend_slave |
| tendbcluster | spider_master | spider_master | remote_master | remote_slave |
| tendbsingle | orphan | — | orphan | — |

### Step 1：并发拉取慢查询 + 监控指标

调用 `collect.sh` 并发采集每个集群的慢查询和监控指标：

```bash
bash scripts/collect.sh <domain> <cluster_type> <slowlog_role> \
  "<analysis_start>" "<analysis_end>" "<baseline_date>" \
  "<metrics_start>" "<metrics_end>"
```

脚本内部自动处理：
- 慢查询 4 个 metric（query_time_max / count_star / rows_examined_max / query_time_sum），分析时段 + 基准时段各一次
- 监控指标（cpu_summary / qps_summary），分析时段 + 基准时段各一次
- 新增 digest 的 EXPLAIN 索引分析（跳过 TRUNCATE/CALL/无 db 的语句）
- 串扰防护：每集群内部各 metric 并发，集群间串行
- 数据重查：collect.sh 内部已包含空数据重查逻辑（最多重试 2 次）

### Step 3：完全匹配对比新增 digest

对比逻辑已封装在 `scripts/generate-html.py` 的 `load_digests()` 函数中：

1. 使用 `load_digests('$OUTPUT_DIR/pcr_cur_<domain>_*.json')` 加载本次 4 个 metric 的 digest
2. 使用 `load_digests('$OUTPUT_DIR/pcr_base_<domain>_*.json')` 加载基准 digest
3. 取两集合的差集得到 `truly_new = {k: v for k, v in today.items() if k not in yest}`

### Step 4：慢查询分类

对每条新增 digest 按 SQL 类型归类：

| 类型 | 关键词 |
|------|--------|
| SELECT | query_command=select（无 INTO OUTFILE） |
| SELECT INTO OUTFILE | select … into outfile |
| INSERT | insert / insert … on duplicate key update |
| UPDATE | update |
| DELETE | delete |
| REPLACE | replace |
| TRUNCATE | truncate |
| CALL | call |
| OTHER | 其他 |

### Step 4.5：EXPLAIN 索引分析

EXPLAIN 采集已由 `collect.sh` 内部自动完成（Step 1 中一并执行），无需单独调用。

`collect.sh` 内部对新增 digest + 今日 Top20（按 qt_sum + cnt 去重合并）执行 EXPLAIN，结果写入 `$OUTPUT_DIR/pcr_explain_<domain>_<digest>.json`。

**索引判断规则**（报告生成时使用）：

| 误报情况 | 处理方式 |
|---|---|
| `Extra: no matching row in const table` | ✅ 索引正常，不得误判为索引问题 |
| EXPLAIN `rows` 远大于 `rows_examined_max` | 以 `rows_examined_max` 为准 |
| `key=NULL` 且 `Extra: no matching row` | ✅ 索引正常 |
| INSERT/REPLACE VALUES 无法 EXPLAIN | 跳过 |

| EXPLAIN 字段 | 判断条件 | 建议 |
|---|---|---|
| type | ALL | ⚠️ 全表扫描 |
| type | index 且 rows_examined_max 大 | ⚠️ 全索引扫描 |
| key | NULL 且无 no matching row | ⚠️ 未命中索引 |
| Extra | Using filesort | ⚠️ 文件排序 |
| Extra | Using temporary | ⚠️ 临时表 |
| type | eq_ref/ref/range/const | ✅ 索引正常 |

### Step 5：解析监控指标

监控指标解析逻辑已封装在 `scripts/generate-html.py` 的 `get_stat()` 函数中：

- 按 `instance_role` 过滤监控数据系列
- 返回 `(avg, max)` 元组

变化判定阈值：
- CPU：delta > 3% → ↑，< -3% → ↓，否则 ≈
- QPS：delta/baseline > 20% → ↑，< -20% → ↓，否则 ≈

### Step 6：生成报告

默认生成 HTML 报告，同时输出 Markdown 到 chat。

**HTML/MHTML 报告**（内嵌 Chart.js 图表，输出 `.mhtml` 文件，发送给用户）：

```bash
python3 scripts/generate-html.py \
  --domains "<domain1>,<domain2>,..." \
  --analysis-start "<analysis_start>" \
  --analysis-end   "<analysis_end>" \
  --baseline-date  "<baseline_date>" \
  --metrics-start  "<metrics_start>" \
  --metrics-end    "<metrics_end>" \
  --metrics-baseline-start "<metrics_baseline_start>" \
  --metrics-baseline-end   "<metrics_baseline_end>" \
  [--cluster-types "<domain>:tendbcluster,..."] \
  --output $OUTPUT_DIR/perf_compare_report_<YYYYMMDD>.html
```

生成后使用 wecom-send-media skill 通过 `MEDIA:` 指令发送 HTML 文件给用户。

报告包含以下部分（section 顺序固定，不得调整）：
1. **综合概览**（`id="overview"`）：每集群状态卡片一览
2. **综合结论**（`id="conclusion"`）：独立 section，含完整 `</tbody></table></div>` 关闭，不嵌套在其他 section 内
3. **监控图表对比**（`id="charts"`）：CPU/QPS 柱状图
4. **新增慢查询汇总**（`id="slowlog"`）：本次 digest / 基准 digest / 新增数
5. **新增慢查询明细**（`id="slowlog-detail"`）：按集群 + SQL 类型归类，含 digest、db、SQL 指纹、cnt、qt_max、rows_ex
6. **CPU 对比表**（`id="cpu"`）：每集群 × 每角色，avg/max + 变化
7. **QPS 对比表**（`id="qps"`）：同上
8. **慢查询总体分析**（`id="slowlog-analysis"`）：Top N 筛选表格，含查询按钮、风险筛选、导出

导航栏顺序与 section 顺序保持一致：概览 → 结论 → 图表 → 慢查询 → 慢查询明细 → CPU → QPS → 慢查询分析

**HTML 格式规范（必须遵守）：**

- SQL 指纹截断：400 字符（二节 + 五节/八节均统一）
- Top N 语义：用户输入 N → qt_sum TopN + cnt TopN 去重，前端 JS 动态算 topSet
- 标记列：⚠️ 有风险 / ✅ 无风险（基于 `is_issue`，非 `is_new`）
- 列支持人工伸缩（makeResizable 拖拽手柄）
- 风险筛选下拉 + 查询按钮（点击触发 saQuery）
- 业务函数（saQuery/saExport/makeResizable/saInitAll）单独 `<script>` 标签，位于 Chart.js `<script>` 之前
- Chart.js 内嵌（使用本地 chart.umd.min.js，无 CDN 依赖）
- 不做行颜色区分（无 row-issue CSS/class）
- 不依赖 CDN 或外部库
- Charts IIFE 使用 ES5 语法（var、function()）

## 注意事项

- 严禁直连数据库
- 所有数据通过 MCP 接口获取
- 分批并发逻辑已在脚本内部处理（fetch_topo.py / collect.sh 使用并发池并发控制）
- collect.sh 内部已包含空数据重查逻辑（最多重试 2 次）
- 报告输出 Markdown 格式，发送到当前会话
