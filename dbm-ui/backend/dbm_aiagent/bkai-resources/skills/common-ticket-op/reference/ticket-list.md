# 单据查询

## 工作流程

### 第一步：查询单据

⛔ **`bk_biz_id`、`ticket_ids`、`cluster_domains` 三个参数至少传一个**，全空会被服务端拒绝。

📌 **`time_duration` 默认查 7 天**，必须主动传 `"7 00:00:00"`（后端默认只有 2 天，不传就覆盖不到）。用户明确指定其他时间范围时按用户的来。

```bash
dbm-mcp-cli call bkdbm-mcp-prod-ticket-op.ticket_op_ticket_list \
  body_param='{<至少一个过滤条件>, "time_duration": "7 00:00:00"}' \
  --raw-query "<用户原始问题>"
```

**必传参数（三选一，至少传一个）：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bk_biz_id` | int | 按业务 ID 过滤 |
| `ticket_ids` | int 数组 | 按单据 ID 过滤 |
| `cluster_domains` | string 数组 | 按集群域名过滤 |

**默认参数（每次都传，除非用户另有指定）：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `time_duration` | string | `"7 00:00:00"` | 查询时间范围，见下方格式说明 |

#### `time_duration` 格式（Django DurationField）

格式严格为 `"<天数> HH:MM:SS"`（**天数和时分秒之间用一个空格分隔**，时分秒部分都是 `00:00:00`）。**禁止**写成 `"15d"`、`"P15D"`、`"15 days"`、`"15:00:00:00"` 等任何其他形式。

按用户描述的天数，照下表替换 `<天数>` 即可：

| 用户说 | 必须传 |
|--------|--------|
| 1 天 / 一天 / 24 小时 | `"1 00:00:00"` |
| 3 天 | `"3 00:00:00"` |
| 7 天 / 一周（默认） | `"7 00:00:00"` |
| 15 天 / 半个月 | `"15 00:00:00"` |
| 30 天 / 一个月 | `"30 00:00:00"` |
| N 天 | `"N 00:00:00"`（把 N 替换成具体数字） |

⚠️ 不要传空字符串、`null` 或省略该字段，否则会被后端 `DurationField` 拒绝。

**可选参数（用户明确提及时才传）：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `statuses` | string 数组 | 按状态过滤（PENDING / APPROVE / RESOURCE_REPLENISH / TODO / TIMER / RUNNING / FAILED / SUCCEEDED / TERMINATED / REVOKED） |

### 第二步：结果展示

按状态分组，以 Markdown 表格输出：

| 单据ID | 类型 | 提单人 | 状态 | 关联集群 | 当前流程 | 耗时 | 创建时间 |
|--------|------|--------|------|---------|---------|------|---------|
| ticket_id | ticket_type | creator | status | relate_clusters | current_flow | cost_time_seconds 转为可读格式 | created_at |

### 第三步：分析

- 统计各状态单据数量
- 标注 RUNNING 状态且耗时超过 1 小时的单据为"执行时间较长"
- 标注 FAILED 状态的单据，输出 `msgs` 中的错误信息
- 结尾汇总：`共 N 张单据（RUNNING: x, FAILED: y, ...）`
