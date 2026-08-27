# 执行单据

> **安全约束**：调用前必须向用户确认。输出待执行的 ticket_id 和关联集群，等用户明确同意后再执行。

## 工作流程

### 第一步：确定 ticket_id

⛔ `ticket_id` 为强制必填参数。用户未提供时，立即要求用户补充，禁止继续执行。

⛔ `ticket_id` is MANDATORY. If not provided, ask the user immediately. Do NOT proceed.

### 第二步：确认

向用户展示以下信息并等待确认：
- 单据 ID
- 单据类型
- 关联集群
- 当前状态

**必须等用户明确回复确认后才能继续。**

### 第三步：执行

```bash
dbm-mcp-cli call bkdbm-mcp-prod-ticket-op.ticket_op_ticket_execute \
  body_param='{"ticket_id": <ticket_id>}' \
  --raw-query "<用户原始问题>"
```

输出执行结果（返回的 `status`）。
