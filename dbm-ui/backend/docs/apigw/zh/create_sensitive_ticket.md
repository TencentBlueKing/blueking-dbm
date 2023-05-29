### 功能描述

创建单据

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号

### 请求参数

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| bk_biz_id | int | 是 | 业务ID |
| ticket_type | string | 是 | 单据类型 |
| details | dict | 是 | 单据差异化参数。详见后面不同单据类型的定义 |
| ignore_duplication | bool | 否 | 是否忽略重复创建单据 |
| remark | string | 否 | 单据备注 |

#### 创建强制变更SQL单据(无模拟执行)

#### details的定义：

| 字段                | 类型            | 必选 | 描述                     |
| ------------------- | --------------- | ---- | ------------------------ |
| cluster_type        | string          | 是   | 集群类型                 |
| backup              | array of object          | 否   | 备份(object定义详见下面)|
| charset             | string          | 是   | 字符集(mysql字符集，默认default) |
| bk_biz_id           | int             | 是   | 业务ID                   |
| cluster_ids         | array of int    | 是   | 集群ID列表               |
| import_mode         | string          | 是   | 导入模式(file-文件上传 / manual-手动输入) |
| ticket_mode         | object          | 是   | 工单模式(详见下面)                 |
| execute_sql_content | string          | 否   | 执行的SQL内容            |
| execute_sql_files | array of file          | 否   | sql执行文件列表            |
| execute_db_infos    | array of object | 是   | 执行数据库信息(object定义详见下面)           |

注：
- import_mode决定SQL文件的上传方式，如果为manual则execute_sql_content不为空。如果是file，则execute_sql_files不为空
- ticket_mode决定是人工确认 / 定时执行
- 单据类型有：TENDBCLUSTER_FORCE_IMPORT_SQLFILE / MYSQL_FORCE_IMPORT_SQLFILE

##### ticket_mode
| 字段                | 类型            | 必选 | 描述                     |
| ------------------- | --------------- | ---- | ------------------------ |
| mode        | string          | 是   | 单据执行模式(manual / timer)|
| trigger_time                | time          | 否   | 在执行模式为timer的时候，需要输入定时执行时间 |

##### execute_db_info
| 字段                | 类型            | 必选 | 描述                     |
| ------------------- | --------------- | ---- | ------------------------ |
| dbnames        | array of string          | 是   | 目标变更DB                 |
| ignore_dbnames                | array of string          | 是   | 忽略DB                     |

##### backup
| 字段                | 类型            | 必选 | 描述                     |
| ------------------- | --------------- | ---- | ------------------------ |
| backup_on        |  string          | 否   | 备份源                 |
| db_patterns                | array of string          | 是   | 匹配DB列表                     |
| table_patterns                | array of string          | 是   | 匹配Table列表                     |
| ignore_dbs                | array of string          | 否   | 忽略DB列表                     |
| ignore_tables                | array of string          | 否   | 忽略Table列表                     |


### 请求参数示例

```json
{
    "ignore_duplication": true,
    "bk_biz_id": 3,
    "ticket_type": "TENDBCLUSTER_FORCE_IMPORT_SQLFILE",
    "remark": "",
    "details": {
        "cluster_type": "tendbcluster",
        "backup": [],
        "charset": "default",
        "bk_biz_id": 3,
        "cluster_ids": [
            129,
            133
        ],
        "import_mode": "file",
        "ticket_mode": {
            "mode": "auto",
            "trigger_time": ""
        },
        "execute_sql_content": "CREATE DATABASE IF NOT EXISTS kio123;",
        "execute_db_infos": [
            {
                "dbnames": [
                    "test"
                ],
                "ignore_dbnames": []
            }
        ]
    }
}
```

### 返回结果示例

```json
{
    "id": 1885,
    "creator": "admin",
    "create_at": "2024-01-29T00:00:44+08:00",
    "updater": "admin",
    "update_at": "2024-01-29T00:00:44+08:00",
    "ticket_type": "TENDBCLUSTER_FORCE_IMPORT_SQLFILE",
    "status": "PENDING",
    "remark": "xxx",
    "group": "tendbcluster",
    "details": {
        "ignore_duplication": true,
        "bk_biz_id": 3,
        "ticket_type": "TENDBCLUSTER_FORCE_IMPORT_SQLFILE",
        "remark": "",
        "details": {
            "cluster_type": "tendbcluster",
            "backup": [],
            "charset": "default",
            "bk_biz_id": 3,
            "cluster_ids": [
                129,
                133
            ],
            "import_mode": "file",
            "ticket_mode": {
                "mode": "auto",
                "trigger_time": ""
            },
            "execute_sql_content": "CREATE DATABASE IF NOT EXISTS kio123;",
            "execute_db_infos": [
                {
                    "dbnames": [
                        "test"
                    ],
                    "ignore_dbnames": []
                }
            ]
        }
    },
    "ticket_type_display": "TenDB Cluster 强制变更SQL执行",
    "status_display": "等待中",
    "cost_time": 1,
    "bk_biz_name": "DBA",
    "db_app_abbr": "dba",
    "ignore_duplication": false,
    "send_msg_config": {},
    "bk_biz_id": 3,
    "is_reviewed": false
}
```

### 返回结果参数说明

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| id | int | 是 | 单据ID |
| creator | string | 是 | 单据创建者 |
| create_at | string | 是 | 单据创建时间 |
| updater | string | 是 | 单据更新者 |
| update_at | string | 是 | 单据更新时间 |
| ticket_type | string | 是 | 单据类型 |
| status | string | 是 | 单据状态 |
| remark | string | 是 | 单据备注 |
| group | string | 是 | 单据所属组 |
| details | dict | 是 | 单据差异化参数，详见单据类型的details定义 |
| ticket_type_display | string | 是 | 单据类型展示名 |
| status_display | string | 是 | 单据状态展示名 |
| cost_time | int | 是 | 单据流转时间 |
| bk_biz_name | string | 是 | 业务名 |
| db_app_abbr | string | 是 | 业务英文名 |
| ignore_duplication | string | 否 | 是否忽略单据重复提交 |
| send_msg_config | dict | 否 | 单据通知配置 |
| bk_biz_id | string | 是 | 单据ID |
| is_reviewed | bool | 是 | 单据是否已被review |