### 功能描述

第三方权限申请 MySQL 高可用集群小额绿通部署。

调用此接口会自动创建 `MYSQL_HA_APPLY_QUICK_MINOR_PASS` 类型的单据，该单据**免审批、无需人工确认**，直接进入部署执行流程。

### 请求参数

| 字段        | 类型   | 必选 | 描述                   |
| ----------- | ------ | ---- | ---------------------- |
| bk_biz_id   | int    | 是   | 业务ID                 |
| ticket_type | string | 是   | 单据类型，固定传 `MYSQL_HA_APPLY_QUICK_MINOR_PASS` |
| remark      | string | 是   | 单据备注（当前实现直接读取 `request.data["remark"]`，因此必须传） |
| details     | dict   | 是   | 单据详情（接口会基于该输入自动补充部署所需字段），详见下面定义 |

#### details

| 字段          | 类型   | 必选 | 描述                                                         |
| ------------- | ------ | ---- | ------------------------------------------------------------ |
| bk_cloud_id   | int    | 是   | 云区域ID                                                     |
| db_module_id  | int    | 是   | DB模块ID，系统会根据该模块ID自动获取对应的 MySQL 版本，版本须在系统配置的小额绿通允许版本列表中 |
| city_code     | string | 是   | 城市代码，用于指定资源池的地域                               |
| domain_key    | string | 是   | 域名关键字。接口内部会自动转换为 `details.domains=[{"key": domain_key}]` |

> 说明：接口在创建单据前会自动补充 `spec`、`cluster_count`、`inst_num`、`ip_source`、`resource_spec` 等字段，并写入单据 `details`。

### 请求参数示例

```json
{
    "bk_biz_id": 3,
    "ticket_type": "MYSQL_HA_APPLY_QUICK_MINOR_PASS",
    "remark": "小额绿通部署申请",
    "details": {
        "bk_cloud_id": 0,
        "db_module_id": 10,
        "city_code": "sz",
        "domain_key": "mydb"
    }
}
```

### 返回结果示例

```json
{
    "id": 2001,
    "creator": "admin",
    "create_at": "2024-01-29T00:00:44+08:00",
    "updater": "admin",
    "update_at": "2024-01-29T00:00:44+08:00",
    "bk_biz_id": 3,
    "ticket_type": "MYSQL_HA_APPLY_QUICK_MINOR_PASS",
    "group": "mysql",
    "status": "PENDING",
    "remark": "小额绿通部署申请",
    "details": {
        "bk_cloud_id": 0,
        "db_module_id": 10,
        "city_code": "sz",
        "spec": "",
        "cluster_count": 1,
        "inst_num": 1,
        "ip_source": "resource_pool",
        "domains": [
            {
                "key": "mydb",
                "master": "mysql.test_module.mydb.dba.db",
                "slave": "mysql-slave.test_module.mydb.dba.db"
            }
        ],
        "resource_spec": {
            "backend_group": {
                "location_spec": {
                    "city": "sz"
                }
            },
            "proxy": {
                "location_spec": {
                    "city": "sz"
                }
            }
        },

        "db_version": "MySQL-8.0",
        "charset": "utf8mb4",
        "db_module_name": "test_module",
        "city_name": "深圳",
        "spec_display": "",
        "bk_cloud_name": "default"
    },
    "send_msg_config": {},
    "config": {
        "send_msg_config": {},
        "helpers": []
    },
    "is_reviewed": false,
    "ignore_duplication": false,
    "todo_operators": [],
    "todo_helpers": [],
    "ticket_type_display": "MySQL高可用小额绿通部署",
    "status_display": "等待中",
    "cost_time": 1,
    "bk_biz_name": "DBA",
    "db_app_abbr": "dba"
}
```

### 返回结果参数说明

| 字段                | 类型   | 描述                                                         |
| ------------------- | ------ | ------------------------------------------------------------ |
| id                  | int    | 单据ID                                                       |
| creator             | string | 单据创建者                                                   |
| create_at           | string | 单据创建时间                                                 |
| updater             | string | 单据更新者                                                   |
| update_at           | string | 单据更新时间                                                 |
| bk_biz_id           | int    | 业务ID                                                       |
| ticket_type         | string | 单据类型，固定为 `MYSQL_HA_APPLY_QUICK_MINOR_PASS`           |
| group               | string | 单据所属组                                                   |
| status              | string | 单据状态                                                     |
| remark              | string | 单据备注                                                     |
| details             | dict   | 单据详情（包含入参和系统自动补充字段）                       |
| send_msg_config     | dict   | 兼容字段，单据通知配置                                       |
| config              | dict   | 单据配置（含 `send_msg_config`、`helpers` 等）              |
| is_reviewed         | bool   | 单据是否已被 review                                          |
| ignore_duplication  | bool   | 是否忽略单据重复提交                                         |
| todo_operators      | list   | 当前待办处理人列表                                           |
| todo_helpers        | list   | 当前待办协助人列表                                           |
| ticket_type_display | string | 单据类型展示名                                               |
| status_display      | string | 单据状态展示名                                               |
| cost_time           | int    | 单据流转时间（秒）                                           |
| bk_biz_name         | string | 业务名                                                       |
| db_app_abbr         | string | 业务英文名                                                   |

### 错误说明

| 错误场景                                   | 说明                                                         |
| ------------------------------------------ | ------------------------------------------------------------ |
| 版本不在允许列表中                         | 根据 `db_module_id` 获取到的 MySQL 版本不在系统配置的小额绿通允许版本列表（`QUICK_MINOR_POAA` 系统配置）中，接口返回校验错误 |
| 缺少 `remark`                              | 当前实现会直接读取 `request.data["remark"]`，未传会导致请求失败，因此该字段必须传 |