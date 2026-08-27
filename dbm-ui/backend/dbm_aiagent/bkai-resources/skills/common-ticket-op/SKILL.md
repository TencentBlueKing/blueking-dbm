---
name: common-ticket-op
description: 单据操作（查询、终止、执行）。当用户查看单据列表、终止单据、取消单据、执行单据、继续单据时触发。
metadata: {"version":"1.0.4","space_id":"1d3d86fa67bef8c3","bk_skill_code":"common-ticket-op","is_public":false,"bkai-dependencies":{"envs":[{"key":"DBM_MCPS","description":"dbm mcp server 地址列表","required":true,"default":"bkdbm-mcp-prod-ticket-op","secret":false},{"key":"OUTPUT_DIR","description":"skills 产物输出路径","required":false,"default":".storage/session","secret":false}]}}
---

# 单据操作

## 意图识别

根据用户意图，读取对应的子文件并按其流程执行：

| 用户意图 | 读取文件 |
|---------|---------|
| 查看单据、单据列表、单据状态、单据进度 | `reference/ticket-list.md` |
| 终止单据、取消单据、停掉单据 | `reference/ticket-terminate.md` |
| 执行单据、继续单据、重试单据 | `reference/ticket-execute.md` |

子文件位于本 SKILL.md 同目录下的 `reference/` 目录中。

⛔ **无明确动词时，禁止直接反问。必须先按 `reference/ticket-list.md` 完成查询并输出结果，再询问用户下一步操作。**

⛔ **When no clear verb is identified, NEVER ask the user first. You MUST query and display results via `reference/ticket-list.md` BEFORE asking what to do next.**

⛔ **终止和执行操作，`ticket_id` 是强制必填参数。用户未提供时，立即要求用户补充，禁止自行查询单据列表推测。**

⛔ **`ticket_id` is MANDATORY for terminate and execute. If not provided, ask the user immediately. NEVER guess or query the ticket list on your own.**

⛔ **终止和执行操作，必须在调用 `dbm-mcp-cli` 之前获得用户的二次确认。先展示 ticket_id、单据类型、关联集群、当前状态，明确告知即将执行的操作，等用户明确回复"确认"后才能调用。未经确认直接调用是严重违规。**

⛔ **For terminate and execute, you MUST obtain explicit user confirmation BEFORE calling `dbm-mcp-cli`. Display ticket_id, ticket type, related clusters, and current status. Clearly state what action will be taken. Wait for the user to explicitly confirm. Calling without confirmation is a CRITICAL VIOLATION.**

## 注意事项

- `ticket-list`：`bk_biz_id` / `ticket_ids` / `cluster_domains` **三个至少传一个**（服务端校验），全空会报错
- `ticket-terminate` / `ticket-execute`：`bk_biz_id` 不需要，只传 `ticket_id`
- 所有参数必须包裹在 `body_param` 中
- 禁止将用户原始语句直接塞入参数值
