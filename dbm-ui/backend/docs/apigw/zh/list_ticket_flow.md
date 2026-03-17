### 功能描述

本接口用于查询单据的流程

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号

### 路由参数

| 字段 | 类型 | 必选 | 描述   |
|----| ---- | ---- |------|
| id | int | 是 | 单据ID |

### 返回结果示例

```json
[
    {
        "id": 8448,
        "status": "SUCCEEDED",
        "todos": [],
        "url": "http://apps.xxx.xxx.com/bk--itsm/#/ticket/detail?id=6191",
        "start_time": "2024-08-13T15:50:01+08:00",
        "end_time": "2024-08-13T15:50:09+08:00",
        "cost_time": 8,
        "flow_type_display": "单据审批",
        "summary": "admin 已处理【审批】(通过)",
        "flow_output": {},
        "create_at": "2024-08-13T15:50:01+08:00",
        "update_at": "2024-08-13T15:50:10+08:00",
        "flow_type": "BK_ITSM",
        "flow_alias": "单据审批",
        "flow_obj_id": "REQ20240813000005",
        "details": {},
        "err_msg": null,
        "err_code": null,
        "retry_type": null,
        "context": {},
        "ticket": 3250
    },
    {
        "id": 8449,
        "status": "RUNNING",
        "todos": [
            {
                "id": 1589,
                "operators": [
                    "admin"
                ],
                "cost_time": 15785,
                "name": "【SQLServer 库表备份】流程待确认，是否继续？",
                "type": "APPROVE",
                "context": {
                    "flow_id": 8449,
                    "ticket_id": 3250
                },
                "status": "TODO",
                "done_by": "",
                "done_at": null,
                "flow": 8449,
                "ticket": 3250
            }
        ],
        "url": null,
        "start_time": "2024-08-13T15:50:01+08:00",
        "end_time": "2024-08-13T15:50:10+08:00",
        "cost_time": 15794,
        "flow_type_display": "SQLServer 库表备份",
        "summary": "暂停状态执行中",
        "flow_output": {},
        "create_at": "2024-08-13T15:50:01+08:00",
        "update_at": "2024-08-13T15:50:10+08:00",
        "flow_type": "PAUSE",
        "flow_alias": "人工确认",
        "flow_obj_id": "pause_aa6910d0594811efae5b5e5314251c78",
        "details": {},
        "err_msg": null,
        "err_code": null,
        "retry_type": null,
        "context": {},
        "ticket": 3250
    },
    {
        "id": 8450,
        "status": "PENDING",
        "todos": [],
        "url": "",
        "start_time": null,
        "end_time": null,
        "cost_time": 0,
        "flow_type_display": "SQLServer 库表备份执行",
        "summary": "",
        "flow_output": {},
        "create_at": "2024-08-13T15:50:01+08:00",
        "update_at": "2024-08-13T15:50:01+08:00",
        "flow_type": "INNER_FLOW",
        "flow_alias": "SQLServer 库表备份执行",
        "flow_obj_id": "",
        "details": {},
        "err_msg": null,
        "err_code": null,
        "retry_type": "manual_retry",
        "context": {},
        "ticket": 3250
    }
]
```

### 返回结果参数说明
返回的是当前单据的todo列表。

| 字段 | 类型     | 必选 | 描述           |
| ---- |--------| ---- |--------------|
| id | int    | 是 | 流程ID         |
| status | str   | 是 | 流程状态          |
| todos | list   | 是 | 流程代办合集          |
| url | str | 是 | 流程详情链接         |
| cost_time | string | 是 | 流程完成时间          |
| summary | string | 是 | 流程总结         |
| flow_output | json | 是 | 流程输出         |
| flow_type | str   | 是 | 流程类型        |
| flow_obj_id | int | 是 | 流程唯一ID         |
| details | json | 是 | 流程的差异化参数，不同的单据类型/流程类型，details也不同        |
| err_msg | string | 是 | 流程错误信息       |
| err_code | int    | 是 | 流程错误代码         |
| retry_type | str    | 是 | 重试类型         |
| context | dict    | 是 | 流程上下文         |
| ticket | int    | 是 | 关联单据ID         |

#### status枚举值
"PENDING"    -- 等待中
"RUNNING"    -- 执行中
"SUCCEEDED"  -- 成功
"TERMINATED" -- 终止
"FAILED"     -- 失败
"REVOKED"    -- 撤销
"SKIPPED"    -- 跳过