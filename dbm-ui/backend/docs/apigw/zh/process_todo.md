### 功能描述

本接口用于确认暂停节点

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

### 请求参数

| 字段 | 类型 | 必选 | 描述            |
| ---- | ---- | ---- |---------------|
| todo_id | int | 是 | 代办ID          |
| action | string | 是 | 动作类型          |
| params | dict | 是 | todo差异化参数。目前为{} |

目前动作类型支持三种：
* APPROVE: 确认执行
* TERMINATE: 终止单据

### 请求参数示例

```json
{
  "action": "TERMINATE",
  "todo_id": 1080,
  "params": {}
}
```

### 返回结果示例

```json
[
  {
    "id": 1080,
    "operators": [
      "admin"
    ],
    "cost_time": 23867,
    "name": "【TBINLOGDUMPER 禁用】流程待确认，是否继续？",
    "type": "APPROVE",
    "context": {
      "flow_id": 6425,
      "ticket_id": 2462
    },
    "status": "DONE_FAILED",
    "done_by": "admin",
    "done_at": "2024-05-13T17:20:35+08:00",
    "flow": 6425,
    "ticket": 2462
  }
]
```

### 返回结果参数说明
返回的是当前单据的todo列表。

| 字段 | 类型     | 必选 | 描述           |
| ---- |--------| ---- |--------------|
| id | int    | 是 | 代办ID         |
| operators | list   | 是 | 操作者          |
| cost_time | string | 是 | 花费时间         |
| name | string | 是 | 代办名          |
| type | string | 是 | 代办类型         |
| ticket_type | string | 是 | 单据类型         |
| context | json   | 是 | 代办上下文        |
| status | string | 是 | 代办状态         |
| done_by | string | 是 | 待办完成人        |
| done_at | string | 是 | 代办完成时间       |
| flow | int    | 是 | 流程ID         |
| ticket | int    | 是 | 单据ID         |

### 人工确认示例

1. 首先通过 `list_ticket_flow` 查询单据的flows，找到flow_type为 `pause` 的flow，这个flow就是人工确认节点。

```json
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
```

2. 在flow找到 `todos`, 因为是人工确认，所以数组中只会有一个元素，获取这个todo id。注意，此时要判断流程status为RUNNING，表示流程在这个节点运行

3. 调用此接口，便可以进行人工确认