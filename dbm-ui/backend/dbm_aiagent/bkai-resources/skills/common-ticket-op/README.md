# common-ticket-op

单据操作（查询、终止、执行）。

## 功能

根据用户意图路由到对应的单据操作：查询单据列表、终止单据、执行单据。无明确动词时默认执行查询。

终止和执行操作需要用户提供 ticket_id，且必须经过二次确认。

## 目录结构

```
common-ticket-op/
├── SKILL.md              # skill 主文件（意图路由 + 硬性规则）
├── reference/
│   ├── ticket-list.md        # 查询单据流程
│   ├── ticket-terminate.md   # 终止单据流程
│   └── ticket-execute.md     # 执行单据流程
└── README.md
```

## 使用的 MCP 接口

| 接口 | 用途 |
|---|---|
| `ticket_op_ticket_list` | 查询单据列表 |
| `ticket_op_ticket_terminate` | 终止单据 |
| `ticket_op_ticket_execute` | 执行单据 |

## 使用方式

对 agent 说："帮我查一下 xxx 集群的单据" 或 "终止单据 12345"

## agent 会做什么

1. 识别用户意图（查询 / 终止 / 执行）
2. 无明确动词时默认查询单据列表并展示结果
3. 终止或执行操作需用户提供 ticket_id 并二次确认后才执行

## 触发词

单据查询、单据列表、终止单据、取消单据、执行单据、继续单据、重试单据、ticket

## 依赖

- `common-cluster-base-info`：用户按业务过滤 `ticket-list` 时，可获取 `bk_biz_id`
