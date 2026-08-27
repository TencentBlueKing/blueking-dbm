---
name: dbm-mysql-cluster-skew-report
description: 查询并分析 TenDBHA/TenDBCluster 集群负载倾斜情况，生成倾斜分析报告。当用户要求分析集群负载是否均衡、热点是否迁移、或提到集群负载倾斜/热点跳变时使用。
metadata: {"version":"1.1.3","space_id":"1d3d86fa67bef8c3","bk_skill_code":"dbm-mysql-cluster-skew-report","is_public":false,"bkai-dependencies":{"envs":[{"key":"DBM_MCPS","description":"dbm mcp server 地址列表","required":true,"default":"bkdbm-mcp-prod-ai-report bkdbm-mcp-prod-dbmeta-query bkdbm-mcp-prod-mysql-query","secret":false},{"key":"OUTPUT_DIR","description":"skills 产物输出路径","required":false,"default":".storage/session","secret":false}]}}
---

# MySQL 集群倾斜查询与报告

## 何时使用

- 用户要求查看集群倾斜情况、分析负载是否均衡、热点是否迁移
- 用户提到集群负载倾斜、热点跳变
- 需要解释热点稳定 / 热点迁移 / 倾斜事件含义

## 工作流程

### Step 1：确认查询参数

需要从用户获取以下信息：

| 参数 | 必需 | 说明 |
|------|------|------|
| `cluster_domain` | 是 | 集群域名，必须是 TenDBHA 或 TenDBCluster 类型 |
| `from_date` | 是 | 查询起始时间 |
| `to_date` | 是 | 查询截止时间 |

进入本 skill 时，AGENTS.md 已通过 `common-cluster-base-info` 确认了集群信息（包含 `bk_biz_id`）。

时间参数规则：
- 用户说"昨天"、"过去3天"等自然语言时，自行推算为具体日期
- 若用户未提供时间范围，默认查询最近 4 小时，并告知用户使用的时间范围
- 格式：`YYYY-MM-DDTHH:MM:SS±HH:MM`，必须携带时区偏移

### Step 2：查询数据并生成报告

```bash
python3 {SKILL_DIR}/scripts/generate_skew_report.py generate \
  --bk-biz-id <bk_biz_id> \
  --cluster-domain "<cluster_domain>" \
  --from-date "<from_date>" \
  --to-date "<to_date>" \
  --timezone "<当前时区偏移，如 +08:00>" \
  --raw-query "<用户原始问题>" \
  --out-dir $OUTPUT_DIR
```

脚本自动查询 MCP、分析数据、生成带图表的 HTML 报告，输出三行：
- `SUMMARY: <≤200字摘要>`
- `HTML: <报告路径>`
- `FINDINGS: <findings.json 路径>`

**如果脚本输出 `NO_SKEW: true`，说明查询时段内无倾斜。直接将 `SUMMARY` 告知用户，结束流程，不执行后续步骤。**

### Step 3：撰写解读并注入报告

读取 `$OUTPUT_DIR/findings.json`（仅包含精简的分析结论，不含原始数据，可安全读入上下文）。

每个 group 在 findings 中有 `commentary_keys` 字段，指定了 4 个注入位置。加上一个 `overall` 总结，构造 `$OUTPUT_DIR/commentaries.json`。

**所有 value 必须是 HTML 格式**（用 `<p>`、`<ol>`、`<strong>` 等标签），不要输出纯文本。

```json
{
  "0_overview": "<p>紧跟图表的<strong>整体解读</strong>：概括本组倾斜的核心特征、严重程度、与业务场景的关联推测。</p><p>第二段补充...</p>",
  "0_segments": "<p>对倾斜时段表格的解读：哪些时段最值得关注、时段之间的规律、与业务高峰/定时任务的关联。</p>",
  "0_nodes": "<p>对节点统计的解读：节点间的分化模式、是否有网段级特征、持续冷点的排查建议。</p>",
  "0_deep": "<p>对深度分析结果的补充解读：将统计发现与业务场景串联、给出因果推理和具体排查路径。</p>",
  "overall": "<p>综合全部分组的<strong>最终结论</strong>。</p><ol><li>根因判断</li><li>优先级排序的排查建议</li><li>监控建议</li></ol>"
}
```

key 中的数字对应 group 索引（多个 group 则有 `1_overview`、`1_segments` 等）。

**写作要点**：
- 聚焦代码难以表达的内容：业务场景关联、因果推理、可操作的排查步骤
- 每个 section 的解读要与紧邻的图表/表格形成呼应，帮助用户理解数据含义
- 使用 `<p>` 分段、`<strong>` 强调关键词、`<ol>` 列举步骤，**不要写成一大段**
- **严禁在 HTML 内容中使用双引号 `"`**——因为 value 本身在 JSON 双引号内，嵌套的双引号会导致 JSON 解析失败。需要引用或强调文字时，使用 `<strong>`、`<em>`、`<span>` 等 HTML 标签代替，例如用 `<span>偏低为主</span>` 代替 `"偏低为主"`

注入到报告：

```bash
python3 {SKILL_DIR}/scripts/generate_skew_report.py inject \
  $OUTPUT_DIR/report.html $OUTPUT_DIR/commentaries.json
```

### Step 4：上传报告

```bash
python3 {SKILL_DIR}/scripts/generate_skew_report.py upload $OUTPUT_DIR/report.html \
  --bk-biz-id <bk_biz_id> \
  --cluster-domain "<cluster_domain>" \
  --summary "<Step 2 输出的 SUMMARY>" \
  --raw-query "<用户原始问题>"
```

脚本输出 `REPORT_URL` 和 `REPORT_ID`。**只需告诉用户两样东西：SUMMARY（一句话摘要）和 `REPORT_URL`（可点击的报告链接）。不要只展示 REPORT_ID。不要在聊天中额外生成"核心发现"、"关键结论"、"排查建议"等章节——这些内容已经在报告中以图表和解读的形式完整呈现，在聊天中重复会降低报告的价值。**

## 禁止事项

- MCP 查询结果必须重定向到文件，不在终端直接输出
- 不要读取或展示 `report.html` 的内容
- 只能读取 `findings.json` 用于撰写综合解读，不要读取原始数据文件
- 综合解读控制在 500 字以内
