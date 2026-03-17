### 功能描述

获取单据详情。返回指定单据的完整信息，包括单据状态、流程信息、待办处理人等。

> **注意**：该接口需要具备单据查看（`TICKET_VIEW`）权限。

---

### 路径参数

| 字段 | 类型 | 必选 | 描述   |
| ---- | ---- | ---- | ------ |
| id   | int  | 是   | 单据ID |

---

### 查询参数

| 字段        | 类型 | 必选 | 描述                                                               |
| ----------- | ---- | ---- | ------------------------------------------------------------------ |
| is_reviewed | int  | 否   | 是否标记单据为已读，传非 `0` 整数时会将单据标记为已读（用于与待办联动） |

---

### 请求参数示例

```
GET /tickets/2780/?is_reviewed=1
```

---

### 返回结果示例

```json
{
    "data": {
        "id": 2780,
        "creator": "admin",
        "create_at": "2025-09-30T17:14:52+08:00",
        "updater": "admin",
        "update_at": "2025-09-30T17:14:53+08:00",
        "ticket_type": "MONGODB_REPLICASET_MIGRATE",
        "status": "APPROVE",
        "remark": "",
        "group": "mongodb",
        "details": {
            "infos": [
                {
                    "source_cluster_id": 1001,
                    "target_cluster_id": 1002
                }
            ],
            "specs": {
                "mongodb": {
                    "cpu": 4,
                    "mem": 16,
                    "qps": 100
                }
            },
            "clusters": {
                "1001": {
                    "cluster_type": "MongoReplicaSet",
                    "immute_domain": "mongodb.test.example.db"
                }
            },
            "ip_source": "resource_pool",
            "recycle_hosts": [
                {
                    "bk_host_id": 20001,
                    "ip": "127.0.0.1"
                }
            ]
        },
        "todo_operators": ["admin"],
        "todo_helpers": [],
        "ticket_type_display": "MongoDB 副本集集群迁移",
        "status_display": "待审批",
        "cost_time": 13473273,
        "bk_biz_name": "验收专用业务",
        "db_app_abbr": "only-dba-test",
        "ignore_duplication": false,
        "send_msg_config": {},
        "config": {},
        "bk_biz_id": 27,
        "is_reviewed": false
    },
    "code": 0,
    "result": true,
    "message": "OK",
    "request_id": "7779c5e039e6ae46f45895fd2d7f555c"
}
```

---

### 返回结果参数说明

#### 外层结构

| 字段       | 类型   | 描述                     |
| ---------- | ------ | ------------------------ |
| code       | int    | 返回码，`0` 表示成功     |
| result     | bool   | 请求是否成功             |
| message    | string | 返回信息                 |
| request_id | string | 请求ID                   |
| data       | dict   | 单据详情，详见下表       |

#### data 字段说明

| 字段                | 类型         | 描述                                                         |
| ------------------- | ------------ | ------------------------------------------------------------ |
| id                  | int          | 单据ID                                                       |
| creator             | string       | 单据创建者                                                   |
| create_at           | string       | 单据创建时间（ISO 8601 格式）                                |
| updater             | string       | 单据更新者                                                   |
| update_at           | string       | 单据更新时间（ISO 8601 格式）                                |
| ticket_type         | string       | 单据类型                                                     |
| status              | string       | 单据状态，可选值见下表                                       |
| remark              | string       | 单据备注                                                     |
| group               | string       | 单据所属组                                                   |
| details             | dict         | 单据差异化参数，详见对应单据类型的 details 定义              |
| todo_operators      | list[string] | 当前运行中待办的处理人列表                                   |
| todo_helpers        | list[string] | 当前运行中待办的协助人列表                                   |
| ticket_type_display | string       | 单据类型展示名                                               |
| status_display      | string       | 单据状态展示名                                               |
| cost_time           | int          | 单据流转耗时（秒）                                           |
| bk_biz_name         | string       | 业务名                                                       |
| db_app_abbr         | string       | 业务英文缩写                                                 |
| ignore_duplication  | bool         | 是否忽略单据重复提交                                         |
| send_msg_config     | dict         | 单据通知配置                                                 |
| config              | dict         | 单据配置信息                                                 |
| bk_biz_id           | int          | 业务ID                                                       |
| is_reviewed         | bool         | 单据是否已被 review（已读）                                  |

#### status 可选值

| 值                 | 描述                                                         |
| ------------------ | ------------------------------------------------------------ |
| PENDING            | 等待中                                                       |
| APPROVE            | 待审批                                                       |
| RESOURCE_REPLENISH | 待补货                                                       |
| TODO               | 待执行                                                       |
| TIMER              | 定时中                                                       |
| RUNNING            | 执行中                                                       |
| INNER_TODO         | 待继续（仅展示，不落地DB，表示存在内置任务待办）             |
| SUCCEEDED          | 已完成                                                       |
| FAILED             | 已失败                                                       |
| REVOKED            | 已撤销                                                       |
| TERMINATED         | 已终止                                                       |