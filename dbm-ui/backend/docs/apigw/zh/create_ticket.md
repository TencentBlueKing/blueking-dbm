### 功能描述

创建单据

### 请求参数

| 字段               | 类型   | 必选 | 描述                                       |
| ------------------ | ------ | ---- | ------------------------------------------ |
| bk_biz_id          | int    | 是   | 业务ID                                     |
| ticket_type        | string | 是   | 单据类型                                   |
| details            | dict   | 是   | 单据差异化参数。详见后面不同单据类型的定义 |
| config             | dict   | 否   | 单据配置（如通知配置、协助人）             |
| ignore_duplication | bool   | 否   | 是否忽略重复创建单据                       |
| remark             | string | 否   | 单据备注                                   |

---

#### 创建MySQL授权单据

details的定义：

| 字段                   | 类型 | 必选 | 描述                                                  |
| ---------------------- | ---- | ---- | ----------------------------------------------------- |
| authorize_plugin_infos | list | 是   | 授权数据列表List[authorize_plugin_info]，详见下面定义 |

##### authorize_plugin_info

| 字段             | 类型         | 必选 | 描述                                             |
| ---------------- | ------------ | ---- | ------------------------------------------------ |
| bk_biz_id        | int          | 是   | 业务ID                                           |
| user             | string       | 是   | 授权用户                                         |
| access_dbs       | list[string] | 是   | 准入DB列表                                       |
| source_ips       | list[string] | 是   | 允许访问的来源IP列表                             |
| target_instances | list[string] | 是   | 目标集群域名列表                                 |
| cluster_type     | string       | 是   | 集群类型，分为tendbsingle，tendbha和tendbcluster |

##### 示例

```json
{
    "authorize_plugin_infos": [
        {
            "bk_biz_id": 3,
            "user": "bobo",
            "access_dbs": [
                "bobo",
                "testlin"
            ],
            "source_ips": [
                "127.0.0.1"
            ],
            "target_instances": [
                "spider.test.abc.db"
            ],
            "cluster_type": "tendbcluster"
        }
    ]
}
```


### 请求参数示例

```json
{
    "bk_biz_id": 3,
    "ticket_type": "TENDBCLUSTER_AUTHORIZE_RULES",
    "remark": "xxx",
    "details": {
        "authorize_plugin_infos": [
            {
                "bk_biz_id": 3,
                "user": "bobo",
                "access_dbs": [
                    "bobo",
                    "testlin"
                ],
                "source_ips": [
                    "127.0.0.1"
                ],
                "target_instances": [
                    "spider.test.abc.db"
                ],
                "cluster_type": "tendbcluster"
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
    "ticket_type": "TENDBCLUSTER_AUTHORIZE_RULES",
    "status": "PENDING",
    "remark": "xxx",
    "group": "tendbcluster",
    "details": {
        "authorize_plugin_infos": [
            {
                "bk_biz_id": 3,
                "user": "bobo",
                "access_dbs": [
                    "bobo",
                    "testlin"
                ],
                "source_ips": [
                    "127.0.0.1"
                ],
                "target_instances": [
                    "spider.test.abc.db"
                ],
                "cluster_type": "tendbcluster"
            }
        ]
    },
    "ticket_type_display": "TenDB Cluster 授权",
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

| 字段                | 类型   | 必选 | 描述                                      |
| ------------------- | ------ | ---- | ----------------------------------------- |
| id                  | int    | 是   | 单据ID                                    |
| creator             | string | 是   | 单据创建者                                |
| create_at           | string | 是   | 单据创建时间                              |
| updater             | string | 是   | 单据更新者                                |
| update_at           | string | 是   | 单据更新时间                              |
| ticket_type         | string | 是   | 单据类型                                  |
| status              | string | 是   | 单据状态                                  |
| remark              | string | 是   | 单据备注                                  |
| group               | string | 是   | 单据所属组                                |
| details             | dict   | 是   | 单据差异化参数，详见单据类型的details定义 |
| ticket_type_display | string | 是   | 单据类型展示名                            |
| status_display      | string | 是   | 单据状态展示名                            |
| cost_time           | int    | 是   | 单据流转时间                              |
| bk_biz_name         | string | 是   | 业务名                                    |
| db_app_abbr         | string | 是   | 业务英文名                                |
| ignore_duplication  | bool   | 否   | 是否忽略单据重复提交                      |
| send_msg_config     | dict   | 否   | 单据通知配置                              |
| bk_biz_id           | int    | 是   | 业务ID                                    |
| is_reviewed         | bool   | 是   | 单据是否已被review                        |




#### 创建SQLServer变更SQL单据
details的定义：

| 字段             | 类型      | 必选 | 描述                                                |
| ---------------- | --------- | ---- | --------------------------------------------------- |
| charset          | string    | 否   | 字符集，默认为GBK                                   |
| force            | bool      | 否   | 是否强制执行                                        |
| path             | string    | 否   | 执行路径，默认为/sqlserver/sqlfile                  |
| cluster_ids      | list[int] | 是   | 执行SQL变更目标集群列表                             |
| execute_objects  | list      | 是   | 具体执行信息列表，详见下面定义                      |
| ticket_mode      | dict      | 是   | 执行模式，详见下面定义                              |
| backup           | list      | 否   | 备份信息，详见下面定义                              |
| backup_place     | string    | 否   | 先固定传死在master做备份                            |
| backup_type      | string    | 否   | 备份方式：全量备份/增量备份(full_backup/log_backup) |
| file_tag         | string    | 否   | 默认为MSSQL_FULL_BACKUP 备份保存时间30天            |


##### execute_objects
| 字段           | 类型         | 必选 | 描述              |
| -------------- | ------------ | ---- | ----------------- |
| dbnames        | list[string] | 是   | 变更DB列表        |
| ignore_dbnames | list[string] | 否   | 忽略DB列表        |
| sql_files      | list[string] | 是   | 变更sql文件名列表 |
| import_mode | string | 是 | 导入模式，默认为file (文件上传) 

##### ticket_mode
| 字段         | 类型   | 必选 | 描述                           |
| ------------ | ------ | ---- | ------------------------------ |
| mode         | string | 是   | manual,auto和timer，默认为auto |
| trigger_time | time   | 否   | 当为timer时，需要填写出发时间  |

##### backup
| 字段              | 类型         | 必选 | 描述       |
| ----------------- | ------------ | ---- | ---------- |
| backup_dbs        | list[string] | 是   | 备份DB列表 |
| ignore_backup_dbs | list[string] | 否   | 忽略DB列表 |


### 请求参数示例
```json
{
    "bk_biz_id": 152,
    "ticket_type": "SQLSERVER_IMPORT_SQLFILE",
    "remark": "xxx",
    "ignore_duplication": true,
    "details": {
        "charset": "GBK", 
        "force": false,
        // 执行路径，非必填，默认为/sqlserver/sqlfile
        "path": "/bk-xx/path1/path2",
        "cluster_ids": [
            1,
            2
        ],
        // DB信息
        "execute_objects": [
            {
                "dbnames": [
                    "master"
                ],
                "ignore_dbnames": [
                    "db"
                ],
              	"sql_files": ["a.sql", "b.sql"],
              	"import_mode": "file",
            },
	    {
                "dbnames": [
                    "master"
                ],
                "ignore_dbnames": [
                    "db2"
                ],
              	"sql_files": ["aa.sql", "bb.sql"], 
              	"import_mode": "file",
            }
        ],
        // 执行模式
        "ticket_mode": {
            "mode": "auto", // 分为 manual, auto和timer
            "trigger_time": "2022-11-11T12:11:11+08:00" // 当为timer时，需要填写出发时间
        },
        // 备份信息
        "backup": [
            {
                "backup_dbs": [
                    "db1",
                    "db2"
                ],
              	"ignore_backup_dbs": [
                	"db2"
                ]
            }
        ],
        "backup_place": "master", // 先固定传死先，只在master做备份
        "backup_type": "full_backup/log_backup", // 备份方式：全量备份/增量备份
        "file_tag": "MSSQL_FULL_BACKUP", // 可以不填，默认为MSSQL_FULL_BACKUP 备份保存时间30天
    }
}

```

#### 创建SQLServer数据迁移单据
details的定义：

| 字段             | 类型   | 必选 | 描述                                 |
| ---------------- | ------ | ---- | ------------------------------------ |
| dts_mode         | string | 是   | 迁移方式，支持全量迁移（full）和增量迁移（incr） |
| need_auto_rename | bool   | 是   | 迁移后是否对源DB进行重命名                       |
| infos            | list   | 是   | 迁移详情列表，详见下面定义                       |


##### infos
| 字段             | 类型      | 必选 | 描述                           |
| ---------------- | --------- | ---- | ------------------------------ |
| src_cluster      | int       | 是   | 源集群ID                       |
| dst_cluster_list | list[int] | 是   | 目标集群ID列表                 |
| db_list          | list      | 否   | 库正则                         |
| ignore_db_list   | list      | 否   | 忽略库正则                     |
| rename_infos     | list      | 是   | 重命名DB信息列表，详见下面定义 |

###### rename_infos
| 字段           | 类型   | 必选 | 描述             |
| -------------- | ------ | ---- | ---------------- |
| db_name        | string | 是   | 迁移DB名         |
| target_db_name | string | 是   | 迁移后DB名       |
| rename_db_name | string | 否   | 迁移后源DB重命名 |


### 请求参数示例
```json
{
    "bk_biz_id": 152,
    "ticket_type": "SQLSERVER_FULL_MIGRATE",
    "remark": "xxx",
    "ignore_duplication": true,
    "details": {
        "dts_mode": "full", // 迁移方式，full全量迁移，incr增量迁移
	"need_auto_rename": true, // 迁移后，系统是否对源DB进行重命名
      	"infos": [
            {
                "src_cluster": 1, // 源集群ID
                "dst_cluster_list": [2], // 目标集群ID列表
                "db_list": [], // 库正则，非必填
                "ignore_db_list": [], // 忽略库正则，非必填
                "rename_infos": [
                    {
                        "db_name": "db1",
                        "target_db_name": "db11",
                        "rename_db_name": "db111", // 非必填
                    },
                    {
                        "db_name": "db2",
                        "target_db_name": "db222",
                    }
                ]
            }
        ]
    }
}
```

#### 创建MongoDB清档单据
details的定义：
| 字段    | 类型 | 必选 | 描述           |
| ------- | ---- | ---- | -------------- |
| is_safe | bool | 否   | 是否做安全检测 |
| infos   | list | 是   | 清档信息列表   |


##### infos
| 字段         | 类型   | 必选 | 描述                                                         |
| ------------ | ------ | ---- | ------------------------------------------------------------ |
| cluster_ids  | list   | 是   | 集群ID列表                                                   |
| cluster_type | string | 是   | 集群类型                                                     |
| drop_type    | string | 是   | 删除类型：直接删除表/将表暂时重命名（drop_collection/rename_collection） |
| drop_index   | bool   | 是   | 是否删除索引                                                 |
| ns_filter    | dict   | 是   | 库表选择器                                                   |

###### ns_filter
| 字段           | 类型         | 必选 | 描述          |
| -------------- | ------------ | ---- | ------------- |
| db_patterns    | list[string] | 是   | 匹配DB列表    |
| ignore_dbs     | list[string] | 是   | 忽略DB列表    |
| table_patterns | list[string] | 是   | 匹配Table列表 |
| ignore_tables  | list[string] | 是   | 忽略Table列表 |


### 请求参数示例
```json
{
    "remark": "username",
    "bk_biz_id": 3,
    "ticket_type": "MONGODB_REMOVE_NS",
    "details": {
      	"is_safe": true,
        "infos": [
            {
                "drop_index": true,
              	"drop_type": "drop_collection|rename_collection",
                "cluster_ids": [1, 2, 3, 4],
                "cluster_type": "MongoReplicaSet",
                "ns_filter": {
                    "db_patterns": [
                        "db1*",
                        "db2*"
                    ],
                    "ignore_dbs": [
                        "db11",
                        "db12",
                        "db23"
                    ],
                    "table_patterns": [
                        "*"
                    ],
                    "ignore_tables": [
                        "tb_role1",
                        "tb_mail10"
                    ]
                }
            }
        ]
    }
}
```

#### 创建sqlserver 定点构造单据
details的定义：

| 字段     | 类型 | 必选 | 描述                                        |
| -------- | ---- | ---- | ------------------------------------------- |
| is_local | bool | 是   | 是否代表原地构造，true是，false代表远程构造 |
| infos    | list | 是   | 构造详情列表，详情请看下表                  |
#### infos

| 字段                | 类型   | 必选 | 描述                                                         |
| ------------------- | ------ | ---- | ------------------------------------------------------------ |
| src_cluster         | int    | 是   | 源集群ID                                                     |
| dst_cluster         | int    | 是   | 目标集群ID                                                   |
| db_list             | list   | 否   | 库正则                                                       |
| ignore_db_list      | list   | 否   | 忽略库正则                                                   |
| rename_infos        | list   | 是   | 迁移DB信息                                                   |
| restore_backup_file | dict   | 否   | 备份记录，与 restore_time 二选一                             |
| restore_time        | string | 否   | 回档时间 - 指定时间来进行恢复，如果有这个参数表示为指定备份时间，否则就是指定备份记录 |

#### rename_infos

| 字段           | 类型   | 必选 | 描述           |
| -------------- | ------ | ---- | -------------- |
| db_name        | string | 是   | 源集群库名     |
| target_db_name | string | 是   | 目标集群库名   |
| rename_db_name | string | 否   | 集群重命名库名 |

#### restore_backup_file
| 字段      | 类型   | 必选 | 描述     |
| --------- | ------ | ---- | -------- |
| backup_id | string | 是   | 备份ID   |
| logs      | list   | 是   | 备份日志 |

### 请求参数示例

```json
{
    "bk_biz_id": "xxx",
    "ticket_type": "SQLSERVER_ROLLBACK",
    "details": {
        "is_local": True/False # 是否代表原地构造，true代表是，false代表远程构造
        "infos": [
            {
                "src_cluster": 1,
                "dst_cluster": 2, # 如果是原地构造，target_cluster_id=cluster_id
                "db_list": [],
  				"ignore_db_list": [],
      			"rename_infos": [
                    {
                        "db_name": str,
                        "target_db_name": str,
                        "rename_db_name": str, # 非必填
                    },
                    {
                        "db_name": str,
                        "target_db_name": str,
                        "rename_db_name": str, # 非必填
                    }
                ],
                "restore_backup_file": {
                    "backup_id": xxx,
                    "logs": [...]
                }, # 备份记录来恢复
                "restore_time": "xxxx", # 指定时间来进行恢复，如果有这个参数表示为指定备份时间，否则就是指定备份记录
            }
        ]
    }
}
```

---

## 集群禁用单据

将集群从在线（online）状态切换为禁用（offline）状态，集群停止对外提供服务，但数据不会被删除。

### 支持的 ticket_type

| ticket_type              | 描述                        |
| ------------------------ | --------------------------- |
| MYSQL_SINGLE_DISABLE     | MySQL 单节点禁用            |
| MYSQL_HA_DISABLE         | MySQL 高可用禁用            |
| TENDBCLUSTER_DISABLE     | TenDB Cluster 集群禁用      |
| SQLSERVER_DISABLE        | SQLServer 集群禁用          |
| REDIS_CLOSE              | Redis 集群禁用              |
| KAFKA_DISABLE            | Kafka 集群禁用              |
| HDFS_DISABLE             | HDFS 集群禁用               |
| ES_DISABLE               | ES 集群禁用                 |
| PULSAR_DISABLE           | Pulsar 集群禁用             |
| DORIS_DISABLE            | Doris 集群禁用              |
| VM_DISABLE               | VM 集群禁用                 |
| RIAK_CLUSTER_DISABLE     | Riak 集群禁用               |
| MONGODB_DISABLE          | MongoDB 集群禁用            |

### details 参数说明

不同数据库类型的 `details` 字段结构略有差异，分为以下两类：

#### 类型一：多集群操作（MySQL / TenDB Cluster / SQLServer / MongoDB / Riak）

| 字段        | 类型      | 必选 | 描述                           |
| ----------- | --------- | ---- | ------------------------------ |
| cluster_ids | list[int] | 是   | 集群ID列表，支持同时禁用多个集群 |
| force       | bool      | 否   | 是否强制禁用，默认为 false     |

##### 示例（MySQL 高可用禁用）

```json
{
    "bk_biz_id": 27,
    "ticket_type": "MYSQL_HA_DISABLE",
    "details": {
        "cluster_ids": [100, 101],
        "force": false
    }
}
```

#### 类型二：单集群操作（Redis / Kafka / HDFS / ES / Pulsar / Doris / VM）

| 字段       | 类型 | 必选 | 描述    |
| ---------- | ---- | ---- | ------- |
| cluster_id | int  | 是   | 集群ID  |

##### 示例（Kafka 集群禁用）

```json
{
    "bk_biz_id": 27,
    "ticket_type": "KAFKA_DISABLE",
    "details": {
        "cluster_id": 200
    }
}
```

### 返回结果示例

```json
{
    "id": 1900,
    "creator": "admin",
    "create_at": "2024-01-29T00:00:44+08:00",
    "updater": "admin",
    "update_at": "2024-01-29T00:00:44+08:00",
    "ticket_type": "MYSQL_HA_DISABLE",
    "status": "PENDING",
    "remark": "",
    "group": "mysql",
    "details": {
        "cluster_ids": [100, 101],
        "force": false
    },
    "ticket_type_display": "MySQL 高可用禁用",
    "status_display": "等待中",
    "cost_time": 1,
    "bk_biz_name": "DBA",
    "db_app_abbr": "dba",
    "ignore_duplication": false,
    "send_msg_config": {},
    "bk_biz_id": 27,
    "is_reviewed": false
}
```

---

## 集群销毁单据

将集群彻底销毁，集群数据和元数据将被清理，操作不可逆。

### 支持的 ticket_type

| ticket_type              | 描述                        |
| ------------------------ | --------------------------- |
| MYSQL_SINGLE_DESTROY     | MySQL 单节点删除            |
| MYSQL_HA_DESTROY         | MySQL 高可用删除            |
| TENDBCLUSTER_DESTROY     | TenDB Cluster 集群销毁      |
| SQLSERVER_DESTROY        | SQLServer 集群卸载          |
| REDIS_DESTROY            | Redis 集群删除              |
| REDIS_INSTANCE_DESTROY   | Redis 主从集群删除          |
| KAFKA_DESTROY            | Kafka 集群删除              |
| HDFS_DESTROY             | HDFS 集群删除               |
| ES_DESTROY               | ES 集群删除                 |
| PULSAR_DESTROY           | Pulsar 集群删除             |
| DORIS_DESTROY            | Doris 集群删除              |
| VM_DESTROY               | VM 集群删除                 |
| RIAK_CLUSTER_DESTROY     | Riak 集群销毁               |
| MONGODB_DESTROY          | MongoDB 集群删除            |

### details 参数说明

不同数据库类型的 `details` 字段结构略有差异，分为以下三类：

#### 类型一：多集群操作（MySQL / TenDB Cluster / SQLServer / MongoDB / Riak / Redis 主从集群）

| 字段        | 类型      | 必选 | 描述                           |
| ----------- | --------- | ---- | ------------------------------ |
| cluster_ids | list[int] | 是   | 集群ID列表，支持同时销毁多个集群 |
| force       | bool      | 否   | 是否强制销毁，默认为 false（仅 MySQL/TenDB Cluster/SQLServer 支持） |

##### 示例（MySQL 高可用删除）

```json
{
    "bk_biz_id": 27,
    "ticket_type": "MYSQL_HA_DESTROY",
    "details": {
        "cluster_ids": [100, 101],
        "force": false
    }
}
```

##### 示例（Redis 主从集群删除）

```json
{
    "bk_biz_id": 27,
    "ticket_type": "REDIS_INSTANCE_DESTROY",
    "details": {
        "cluster_ids": [200, 201]
    }
}
```

#### 类型二：单集群操作（Redis 集群 / Kafka / HDFS / ES / Pulsar / Doris / VM）

| 字段       | 类型 | 必选 | 描述    |
| ---------- | ---- | ---- | ------- |
| cluster_id | int  | 是   | 集群ID  |

##### 示例（Redis 集群删除）

```json
{
    "bk_biz_id": 27,
    "ticket_type": "REDIS_DESTROY",
    "details": {
        "cluster_id": 300
    }
}
```

##### 示例（Doris 集群删除）

```json
{
    "bk_biz_id": 27,
    "ticket_type": "DORIS_DESTROY",
    "details": {
        "cluster_id": 400
    }
}
```

### 返回结果示例

```json
{
    "id": 1901,
    "creator": "admin",
    "create_at": "2024-01-29T00:00:44+08:00",
    "updater": "admin",
    "update_at": "2024-01-29T00:00:44+08:00",
    "ticket_type": "MYSQL_HA_DESTROY",
    "status": "PENDING",
    "remark": "",
    "group": "mysql",
    "details": {
        "cluster_ids": [100, 101],
        "force": false
    },
    "ticket_type_display": "MySQL 高可用删除",
    "status_display": "等待中",
    "cost_time": 1,
    "bk_biz_name": "DBA",
    "db_app_abbr": "dba",
    "ignore_duplication": false,
    "send_msg_config": {},
    "bk_biz_id": 27,
    "is_reviewed": false
}
```


---

### MySQL 集群部署类单据

### 功能描述

通过 `/apis/tickets/` 创建 **MySQL 集群部署类单据**，并触发后续单据流程（审批/人工确认/资源申请/部署执行）。

---

## 支持的部署单据类型

| ticket_type          | 说明             | 对应 Builder                  |
| -------------------- | ---------------- | ----------------------------- |
| `MYSQL_SINGLE_APPLY` | MySQL 单节点部署 | `MysqlSingleApplyFlowBuilder` |
| `MYSQL_HA_APPLY`     | MySQL 高可用部署 | `MysqlHAApplyFlowBuilder`     |

---

## 顶层请求参数

| 字段                 | 类型   | 必选 | 描述                                                         |
| -------------------- | ------ | ---- | ------------------------------------------------------------ |
| `bk_biz_id`          | int    | 是   | 业务 ID                                                      |
| `ticket_type`        | string | 是   | 单据类型（本场景为 `MYSQL_SINGLE_APPLY` 或 `MYSQL_HA_APPLY`） |
| `details`            | dict   | 是   | 单据详情，按 `ticket_type` 动态选择序列化器校验              |
| `remark`             | string | 否   | 单据备注                                                     |
| `ignore_duplication` | bool   | 否   | 是否忽略重复单据校验，默认 `false`                           |
| `config`             | dict   | 否   | 单据配置（通知配置、协助人等）                               |

---

## `details` 参数定义

### 通用字段（`MYSQL_SINGLE_APPLY` / `MYSQL_HA_APPLY`）

`MYSQL_HA_APPLY` 的详情序列化器继承自 `MysqlSingleApplyDetailSerializer`，因此以下字段均通用：

| 字段                       | 类型   | 必选     | 描述                                             |
| -------------------------- | ------ | -------- | ------------------------------------------------ |
| `bk_cloud_id`              | int    | 是       | 云区域 ID                                        |
| `city_code`                | string | 否       | 城市代码，可空，默认 `""`                        |
| `spec`                     | string | 否       | 机器规格（兼容展示字段）                         |
| `db_module_id`             | int    | 是       | DB 模块 ID                                       |
| `cluster_count`            | int    | 是       | 申请集群数量，最小值为 1                         |
| `inst_num`                 | int    | 否       | 每台机器部署实例数，默认 `1`                     |
| `ip_source`                | string | 是       | 主机来源：`resource_pool`                        |
| `resource_spec`            | dict   | 条件必选 | 资源池申请规格，详见下文`resource_spec` 参数定义 |
| `domains`                  | list   | 是       | 域名关键字列表，元素格式 `{ "key": "xxx" }`      |
| `start_mysql_port`         | int    | 否       | MySQL 起始端口，默认 `30000`                     |
| `disaster_tolerance_level` | string | 否       | 容灾级别，默认 `NONE`                            |

### `resource_spec` 参数定义

`resource_spec` 在 `ip_source = resource_pool` 时用于资源池申请规格。

`resource_spec` 的定义：

| 字段                 | 类型 | 必选     | 描述                                                         |
| -------------------- | ---- | -------- | ------------------------------------------------------------ |
| `backend`            | dict | 条件必选 | 后端规格对象。`MYSQL_SINGLE_APPLY` 必填；`MYSQL_HA_APPLY` 在流程中由 `master` 转换得到 |
| `master`             | dict | 条件必选 | 主机规格对象。`MYSQL_HA_APPLY` 必填                          |
| `proxy`              | dict | 条件必选 | Proxy 规格对象。`MYSQL_HA_APPLY` 必填                        |
| `resource_spec_item` | dict | 否       | 规格对象结构定义，详见下文 `resource_spec_item`              |
| `location_spec`      | dict | 否       | 地域约束结构定义，详见下文 `location_spec`                   |

##### `resource_spec_item`

| 字段            | 类型 | 必选 | 描述                   |
| --------------- | ---- | ---- | ---------------------- |
| `spec_id`       | int  | 是   | 规格 ID                |
| `count`         | int  | 是   | 申请机器数量           |
| `location_spec` | dict | 否   | 地域约束，详见下面定义 |

##### `location_spec`

| 字段           | 类型      | 必选 | 描述                |
| -------------- | --------- | ---- | ------------------- |
| `city`         | string    | 否   | 城市代码（如 `sz`） |
| `sub_zone_ids` | list[int] | 否   | 园区 ID 列表        |

> 说明：
>
> - `MYSQL_SINGLE_APPLY`：使用 `resource_spec.backend`。
> - `MYSQL_HA_APPLY`：请求参数使用 `resource_spec.master` 与 `resource_spec.proxy`；执行前会将 `master` 转换为 `backend` 供后续流程使用。
> - `MYSQL_HA_APPLY` 场景下，`proxy` 规格会在流程中补充 `group_count = 2`。



### `MYSQL_HA_APPLY` 额外字段

| 字段               | 类型 | 必选 | 描述                         |
| ------------------ | ---- | ---- | ---------------------------- |
| `start_proxy_port` | int  | 否   | Proxy 起始端口，默认 `50000` |

### 域名相关校验规则

- `domains[].key` 不允许重复。
- 会校验集群名/域名是否合法以及是否冲突。

---

## 请求示例（MySQL 集群部署）

```json
{
  "bk_biz_id": 3,
  "ticket_type": "MYSQL_HA_APPLY",
  "remark": "MySQL高可用部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "city_code": "sz",
    "db_module_id": 10,
    "cluster_count": 2,
    "inst_num": 1,
    "ip_source": "resource_pool",
    "resource_spec": {
      "master": {
        "spec_id": 1001,
        "count": 4,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "proxy": {
        "spec_id": 1002,
        "count": 4,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    },
    "domains": [
      { "key": "game_order" },
      { "key": "game_pay" }
    ],
    "start_mysql_port": 30000,
    "start_proxy_port": 50000,
    "disaster_tolerance_level": "NONE"
  }
}
```

---

## 返回结果示例

```json
{
  "id": 1024,
  "bk_biz_id": 3,
  "group": "mysql",
  "ticket_type": "MYSQL_HA_APPLY",
  "ticket_type_display": "MySQL高可用部署",
  "status": "PENDING",
  "status_display": "待审批",
  "remark": "MySQL高可用部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "city_code": "sz",
    "db_module_id": 10,
    "cluster_count": 2,
    "inst_num": 1,
    "ip_source": "resource_pool",
    "resource_spec": {
      "backend": {
        "spec_id": 1001,
        "count": 4,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "proxy": {
        "spec_id": 1002,
        "count": 4,
        "group_count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    },
    "domains": [
      {
        "key": "game_order",
        "master": "mysql.game_order.game.db",
        "slave": "mysql-slave.game_order.game.db"
      },
      {
        "key": "game_pay",
        "master": "mysql.game_pay.game.db",
        "slave": "mysql-slave.game_pay.game.db"
      }
    ],
    "start_mysql_port": 30000,
    "start_proxy_port": 50000,
    "disaster_tolerance_level": "NONE",
    "db_version": "MySQL-8.0",
    "charset": "utf8mb4"
  },
  "todo_operators": [],
  "todo_helpers": [],
  "cost_time": "3s",
  "bk_biz_name": "DBA测试业务",
  "db_app_abbr": "game",
  "create_at": "2026-03-17T15:52:00+08:00",
  "update_at": "2026-03-17T15:52:03+08:00",
  "creator": "admin",
  "updater": "admin"
}
```

## 返回结果字段说明

接口返回 `TicketSerializer` 序列化后的单据对象。

### 顶层字段

| 字段                  | 类型         | 说明                                                       |
| --------------------- | ------------ | ---------------------------------------------------------- |
| `id`                  | int          | 单据 ID                                                    |
| `bk_biz_id`           | int          | 业务 ID                                                    |
| `group`               | string       | 单据分组（MySQL 为 `mysql`）                               |
| `ticket_type`         | string       | 单据类型（如 `MYSQL_SINGLE_APPLY`、`MYSQL_HA_APPLY`）      |
| `ticket_type_display` | string       | 单据类型展示名                                             |
| `status`              | string       | 单据状态（如 `PENDING`、`RUNNING`、`SUCCEEDED`、`FAILED`） |
| `status_display`      | string       | 单据状态展示名                                             |
| `remark`              | string       | 单据备注                                                   |
| `ignore_duplication`  | bool         | 是否忽略重复校验                                           |
| `details`             | dict         | 单据详情（含提交参数及系统补充字段）                       |
| `todo_operators`      | list[string] | 当前待办处理人列表                                         |
| `todo_helpers`        | list[string] | 当前待办协助人列表                                         |
| `cost_time`           | string       | 单据耗时（展示值）                                         |
| `bk_biz_name`         | string       | 业务名称                                                   |
| `db_app_abbr`         | string       | 业务英文缩写                                               |
| `create_at`           | string       | 创建时间                                                   |
| `update_at`           | string       | 更新时间                                                   |
| `creator`             | string       | 创建人                                                     |
| `updater`             | string       | 更新人                                                     |

### `details` 常见字段（MySQL 集群部署）

> `details` 为动态结构，不同单据类型会有差异；以下是 `MYSQL_SINGLE_APPLY` / `MYSQL_HA_APPLY` 常见字段。

| 字段                       | 类型       | 说明                                                     |
| -------------------------- | ---------- | -------------------------------------------------------- |
| `bk_cloud_id`              | int        | 云区域 ID                                                |
| `city_code`                | string     | 城市代码                                                 |
| `db_module_id`             | int        | DB 模块 ID                                               |
| `cluster_count`            | int        | 申请集群数量                                             |
| `inst_num`                 | int        | 每台机器部署实例数                                       |
| `ip_source`                | string     | 主机来源（如 `resource_pool`）                           |
| `resource_spec`            | dict       | 资源规格（可能包含 `backend` / `master` / `proxy`）      |
| `domains`                  | list[dict] | 域名列表；元素通常含 `key`，并可能回填 `master`、`slave` |
| `start_mysql_port`         | int        | MySQL 起始端口                                           |
| `start_proxy_port`         | int        | Proxy 起始端口（HA 常见）                                |
| `disaster_tolerance_level` | string     | 容灾级别                                                 |
| `db_version`               | string     | 数据库版本（系统补充）                                   |
| `charset`                  | string     | 字符集（系统补充）                                       |

### `details.resource_spec` 常见回填说明

| 字段路径                              | 类型 | 说明                                        |
| ------------------------------------- | ---- | ------------------------------------------- |
| `resource_spec.backend.spec_id`       | int  | 后端规格 ID                                 |
| `resource_spec.backend.count`         | int  | 后端机器数量                                |
| `resource_spec.backend.location_spec` | dict | 后端地域约束                                |
| `resource_spec.proxy.spec_id`         | int  | Proxy 规格 ID                               |
| `resource_spec.proxy.count`           | int  | Proxy 机器数量                              |
| `resource_spec.proxy.group_count`     | int  | Proxy 分组数（HA 场景流程补充，通常为 `2`） |
| `resource_spec.proxy.location_spec`   | dict | Proxy 地域约束                              |

## 常见失败场景

- `domains` 中存在重复 `key`。
- 域名/集群关键字冲突或格式不合法。
- `MYSQL_HA_APPLY` 手工选机时机器数量不符合预期规则。
- `details` 结构与 `ticket_type` 不匹配，导致动态序列化校验失败。


---

### MongoDB 集群部署类单据

### 功能描述

通过 `/apis/tickets/` 创建 **MongoDB 集群部署类单据**，并触发后续单据流程（审批/人工确认/资源申请/部署执行）。

---

## 支持的部署单据类型

| ticket_type                | 说明                   | 对应 Builder                          |
| -------------------------- | ---------------------- | ------------------------------------- |
| `MONGODB_REPLICASET_APPLY` | MongoDB 副本集集群部署 | `MongoReplicaSetApplyFlowBuilder`     |
| `MONGODB_SHARD_APPLY`      | MongoDB 分片集群部署   | `MongoShardedClusterApplyFlowBuilder` |

---

## 顶层请求参数

| 字段                 | 类型   | 必选 | 描述                                                         |
| -------------------- | ------ | ---- | ------------------------------------------------------------ |
| `bk_biz_id`          | int    | 是   | 业务 ID                                                      |
| `ticket_type`        | string | 是   | 单据类型（本场景为 `MONGODB_REPLICASET_APPLY` 或 `MONGODB_SHARD_APPLY`） |
| `details`            | dict   | 是   | 单据详情，按 `ticket_type` 动态选择序列化器校验              |
| `remark`             | string | 否   | 单据备注                                                     |
| `ignore_duplication` | bool   | 否   | 是否忽略重复单据校验，默认 `false`                           |
| `config`             | dict   | 否   | 单据配置（通知配置、协助人等）                               |

---

## `details` 参数定义

### `MONGODB_REPLICASET_APPLY`（副本集集群部署）

序列化器：`MongoReplicaSetApplyDetailSerializer`

| 字段                       | 类型   | 必选     | 描述                                                         |
| -------------------------- | ------ | -------- | ------------------------------------------------------------ |
| `bk_cloud_id`              | int    | 是       | 云区域 ID                                                    |
| `db_app_abbr`              | string | 是       | 业务英文缩写                                                 |
| `city_code`                | string | 否       | 城市代码，可空，默认 `""`                                    |
| `disaster_tolerance_level` | string | 否       | 容灾级别，默认 `NONE`，详见下文                              |
| `cluster_type`             | string | 是       | 集群类型，固定为 `MongoReplicaSet`                           |
| `db_version`               | string | 是       | MongoDB 版本号（如 `MongoDB-4.4`）                           |
| `start_port`               | int    | 是       | 副本集起始端口                                               |
| `replica_count`            | int    | 是       | 副本集数量（总共需要部署的副本集个数）                       |
| `node_count`               | int    | 是       | 每个副本集的节点数量                                         |
| `node_replica_count`       | int    | 是       | 单台机器上部署的副本集数量                                   |
| `replica_sets`             | list   | 是       | 副本集列表，元素格式见下文 `replica_sets` 参数定义           |
| `spec_id`                  | int    | 是       | 规格 ID                                                      |
| `oplog_percent`            | int    | 是       | oplog 容量占比（百分比整数，如 `10` 表示 10%）               |
| `ip_source`                | string | 是       | 主机来源：`resource_pool`（资源池）                          |
| `resource_spec`            | dict   | 条件必选 | 资源池申请规格，`ip_source = resource_pool` 时必填，详见下文 |

#### `replica_sets` 元素结构

| 字段     | 类型   | 必选 | 描述                              |
| -------- | ------ | ---- | --------------------------------- |
| `set_id` | string | 是   | 副本集 ID（英文、数字及下划线）   |
| `name`   | string | 是   | 集群别名（允许传空字符串或 null） |
| `domain` | string | 是   | 集群域名                          |

#### `resource_spec`（副本集）参数定义

副本集的资源规格通过 `resource_spec.mongo_machine_set` 描述：

| 字段                | 类型 | 必选 | 描述                                              |
| ------------------- | ---- | ---- | ------------------------------------------------- |
| `mongo_machine_set` | dict | 是   | 副本集节点规格对象，详见下文 `resource_spec_item` |

##### `resource_spec_item`（副本集节点）

| 字段            | 类型   | 必选 | 描述                                       |
| --------------- | ------ | ---- | ------------------------------------------ |
| `spec_id`       | int    | 是   | 规格 ID                                    |
| `count`         | int    | 是   | 申请机器数量（通常等于 `node_count`）      |
| `affinity`      | string | 否   | 亲和性，与 `disaster_tolerance_level` 一致 |
| `location_spec` | dict   | 否   | 地域约束，详见下文 `location_spec`         |

##### `location_spec`

| 字段           | 类型      | 必选 | 描述                |
| -------------- | --------- | ---- | ------------------- |
| `city`         | string    | 否   | 城市代码（如 `sz`） |
| `sub_zone_ids` | list[int] | 否   | 园区 ID 列表        |

> 说明：
>
> - 系统会根据 `replica_count / node_replica_count` 计算出需要申请的机器组数（`groups`），并为每组生成一个 `infos` 条目。
> - 每组 `infos` 中的 `resource_spec.mongo_machine_set` 会在资源申请阶段被转换为 `resource_spec.spec_config`。
> - 当 `disaster_tolerance_level` 为 `SAME_SUBZONE` 或 `SAME_SUBZONE_CROSS_SWTICH` 时，需在 `resource_spec.mongo_machine_set.location_spec.sub_zone_ids` 中指定园区 ID。

---

### `MONGODB_SHARD_APPLY`（分片集群部署）

序列化器：`MongoShardedClusterApplyDetailSerializer`

| 字段                       | 类型   | 必选 | 描述                                   |
| -------------------------- | ------ | ---- | -------------------------------------- |
| `bk_cloud_id`              | int    | 是   | 云区域 ID                              |
| `db_app_abbr`              | string | 是   | 业务英文缩写                           |
| `city_code`                | string | 否   | 城市代码，可空，默认 `""`              |
| `disaster_tolerance_level` | string | 否   | 容灾级别，默认 `NONE`，详见下文        |
| `cluster_type`             | string | 是   | 集群类型，固定为 `MongoShardedCluster` |
| `cluster_name`             | string | 是   | 集群 ID（英文标识）                    |
| `cluster_alias`            | string | 是   | 集群别名（允许传空字符串或 null）      |
| `db_version`               | string | 是   | MongoDB 版本号（如 `MongoDB-4.4`）     |

| `start_port` | int | 是 | 起始端口（同时作为 mongos 的 proxy_port） |
| `oplog_percent` | int | 是 | oplog 容量占比（百分比整数） |
| `ip_source` | string | 是 | 主机来源：`resource_pool`（资源池） |
| `resource_spec` | dict | 是 | 资源申请规格，详见下文 `resource_spec`（分片集群）参数定义 |
| `shard_machine_group` | int | 是 | 机器组数（每组包含 `MONGODB_SHARD_GROUP_COUNT=3` 台 mongodb 节点） |
| `shard_num` | int | 是 | 集群分片数 |

#### `resource_spec`（分片集群）参数定义

分片集群的资源规格包含三类角色：

| 字段           | 类型 | 必选 | 描述                                                    |
| -------------- | ---- | ---- | ------------------------------------------------------- |
| `mongodb`      | dict | 是   | 分片节点（shard）规格，详见下文 `resource_spec_item`    |
| `mongo_config` | dict | 是   | Config Server 节点规格，详见下文 `resource_spec_item`   |
| `mongos`       | dict | 是   | Mongos（接入层）节点规格，详见下文 `resource_spec_item` |

##### `resource_spec_item`（分片集群各角色）

| 字段            | 类型 | 必选 | 描述                               |
| --------------- | ---- | ---- | ---------------------------------- |
| `spec_id`       | int  | 是   | 规格 ID                            |
| `count`         | int  | 是   | 申请机器数量                       |
| `location_spec` | dict | 否   | 地域约束，详见下文 `location_spec` |

> 说明：
>
> - `resource_spec.mongodb` 在资源申请阶段会按 `shard_machine_group` 组数展开为 `mongodb_nodes_0`、`mongodb_nodes_1`、... 等多组，每组默认 3 台（`MONGODB_SHARD_GROUP_COUNT = 3`）。
> - 资源申请完成后，`post_callback` 会将 `mongodb_nodes_0`、`mongodb_nodes_1`、... 聚合回 `nodes.mongodb` 列表。
> - `proxy_port` 在流程中由 `start_port` 自动赋值。
> - 各角色的 `tolerance`（容忍度）由 `disaster_tolerance_level` 自动计算填充，无需手动传入。

---

## 容灾级别（`disaster_tolerance_level`）说明

| 值                          | 说明                       |
| --------------------------- | -------------------------- |
| `NONE`                      | 无（默认）                 |
| `SAME_SUBZONE`              | 指定园区（无机架要求）     |
| `SAME_SUBZONE_CROSS_SWTICH` | 指定园区                   |
| `CROS_SUBZONE`              | 跨园区                     |
| `CROSS_RACK`                | 不限园区                   |
| `MAX_EACH_ZONE_EQUAL`       | 每个 subzone 尽量均匀分布  |
| `CROSS_SUBZONE_STRONG`      | 跨园区（强，MongoDB 专属） |
| `CROSS_SUBZONE_WEAK`        | 跨园区（弱，MongoDB 专属） |

---

## 请求示例

### 示例一：MongoDB 副本集集群部署

```json
{
  "bk_biz_id": 3,
  "ticket_type": "MONGODB_REPLICASET_APPLY",
  "remark": "MongoDB副本集集群部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "city_code": "sz",
    "disaster_tolerance_level": "NONE",
    "cluster_type": "MongoReplicaSet",
    "db_version": "MongoDB-4.4",
    "start_port": 27017,
    "replica_count": 2,
    "node_count": 3,
    "node_replica_count": 1,
    "replica_sets": [
      {
        "set_id": "replicaset_game_order",
        "name": "游戏订单副本集",
        "domain": "mongo.replicaset_game_order.game.db"
      },
      {
        "set_id": "replicaset_game_pay",
        "name": "游戏支付副本集",
        "domain": "mongo.replicaset_game_pay.game.db"
      }
    ],
    "spec_id": 2001,
    "oplog_percent": 10,
    "ip_source": "resource_pool",
    "resource_spec": {
      "mongo_machine_set": {
        "spec_id": 2001,
        "count": 3,
        "affinity": "NONE",
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    }
  }
}
```

### 示例二：MongoDB 分片集群部署

```json
{
  "bk_biz_id": 3,
  "ticket_type": "MONGODB_SHARD_APPLY",
  "remark": "MongoDB分片集群部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "city_code": "sz",
    "disaster_tolerance_level": "NONE",
    "cluster_type": "MongoShardedCluster",
    "cluster_name": "mongo_shard_game",
    "cluster_alias": "游戏分片集群",
    "db_version": "MongoDB-4.4",
    "start_port": 27017,
    "oplog_percent": 10,
    "ip_source": "resource_pool",
    "shard_machine_group": 2,
    "shard_num": 2,
    "resource_spec": {
      "mongodb": {
        "spec_id": 2001,
        "count": 6,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "mongo_config": {
        "spec_id": 2002,
        "count": 3,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "mongos": {
        "spec_id": 2003,
        "count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    }
  }
}
```

---

## 返回结果示例

### 副本集集群部署返回示例

```json
{
  "id": 2048,
  "bk_biz_id": 3,
  "group": "mongodb",
  "ticket_type": "MONGODB_REPLICASET_APPLY",
  "ticket_type_display": "MongoDB 副本集集群部署",
  "status": "PENDING",
  "status_display": "待审批",
  "remark": "MongoDB副本集集群部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "city_code": "sz",
    "disaster_tolerance_level": "NONE",
    "cluster_type": "MongoReplicaSet",
    "db_version": "MongoDB-4.4",
    "start_port": 27017,
    "replica_count": 2,
    "node_count": 3,
    "node_replica_count": 1,
    "replica_sets": [
      {
        "set_id": "replicaset_game_order",
        "name": "游戏订单副本集",
        "domain": "mongo.replicaset_game_order.game.db"
      },
      {
        "set_id": "replicaset_game_pay",
        "name": "游戏支付副本集",
        "domain": "mongo.replicaset_game_pay.game.db"
      }
    ],
    "spec_id": 2001,
    "oplog_percent": 10,
    "ip_source": "resource_pool",
    "resource_spec": {
      "mongo_machine_set": {
        "spec_id": 2001,
        "count": 3,
        "affinity": "NONE",
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    },
    "infos": [
      {
        "bk_cloud_id": 0,
        "resource_spec": {
          "mongo_machine_set": {
            "spec_id": 2001,
            "count": 3,
            "affinity": "NONE",
            "spec_name": "4C8G",
            "location_spec": {
              "city": "sz",
              "sub_zone_ids": []
            },
            "tolerance": 0.5
          }
        }
      },
      {
        "bk_cloud_id": 0,
        "resource_spec": {
          "mongo_machine_set": {
            "spec_id": 2001,
            "count": 3,
            "affinity": "NONE",
            "spec_name": "4C8G",
            "location_spec": {
              "city": "sz",
              "sub_zone_ids": []
            },
            "tolerance": 0.5
          }
        }
      }
    ],
    "bk_app_abbr": "game",
    "zone_list": ["sz_1", "sz_2"]
  },
  "todo_operators": [],
  "todo_helpers": [],
  "cost_time": "2s",
  "bk_biz_name": "DBA测试业务",
  "db_app_abbr": "game",
  "create_at": "2026-03-17T16:00:00+08:00",
  "update_at": "2026-03-17T16:00:02+08:00",
  "creator": "admin",
  "updater": "admin"
}
```

### 分片集群部署返回示例

```json
{
  "id": 2049,
  "bk_biz_id": 3,
  "group": "mongodb",
  "ticket_type": "MONGODB_SHARD_APPLY",
  "ticket_type_display": "MongoDB 分片集群部署",
  "status": "PENDING",
  "status_display": "待审批",
  "remark": "MongoDB分片集群部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "city_code": "sz",
    "disaster_tolerance_level": "NONE",
    "cluster_type": "MongoShardedCluster",
    "cluster_name": "mongo_shard_game",
    "cluster_alias": "游戏分片集群",
    "db_version": "MongoDB-4.4",
    "start_port": 27017,
    "oplog_percent": 10,
    "ip_source": "resource_pool",
    "shard_machine_group": 2,
    "shard_num": 2,
    "resource_spec": {
      "mongodb": {
        "spec_id": 2001,
        "count": 6,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        },
        "tolerance": 0.5
      },
      "mongo_config": {
        "spec_id": 2002,
        "count": 3,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        },
        "tolerance": 0.5
      },
      "mongos": {
        "spec_id": 2003,
        "count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        },
        "tolerance": 0.5
      },
      "mongodb_nodes_0": {
        "spec_id": 2001,
        "count": 3,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "mongodb_nodes_1": {
        "spec_id": 2001,
        "count": 3,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    },
    "bk_app_abbr": "game",
    "proxy_port": 27017,
    "zone_list": ["sz_1", "sz_2"],
    "machine_specs": {
      "mongodb": {"spec_id": 2001, "spec_config": {}},
      "mongo_config": {"spec_id": 2002, "spec_config": {}},
      "mongos": {"spec_id": 2003, "spec_config": {}}
    }
  },
  "todo_operators": [],
  "todo_helpers": [],
  "cost_time": "2s",
  "bk_biz_name": "DBA测试业务",
  "db_app_abbr": "game",
  "create_at": "2026-03-17T16:00:00+08:00",
  "update_at": "2026-03-17T16:00:02+08:00",
  "creator": "admin",
  "updater": "admin"
}
```

---

## 返回结果字段说明

接口返回 `TicketSerializer` 序列化后的单据对象。

### 顶层字段

| 字段                  | 类型         | 说明                                                         |
| --------------------- | ------------ | ------------------------------------------------------------ |
| `id`                  | int          | 单据 ID                                                      |
| `bk_biz_id`           | int          | 业务 ID                                                      |
| `group`               | string       | 单据分组（MongoDB 为 `mongodb`）                             |
| `ticket_type`         | string       | 单据类型（如 `MONGODB_REPLICASET_APPLY`、`MONGODB_SHARD_APPLY`） |
| `ticket_type_display` | string       | 单据类型展示名                                               |
| `status`              | string       | 单据状态（如 `PENDING`、`RUNNING`、`SUCCEEDED`、`FAILED`）   |
| `status_display`      | string       | 单据状态展示名                                               |
| `remark`              | string       | 单据备注                                                     |
| `ignore_duplication`  | bool         | 是否忽略重复校验                                             |
| `details`             | dict         | 单据详情（含提交参数及系统补充字段）                         |
| `todo_operators`      | list[string] | 当前待办处理人列表                                           |
| `todo_helpers`        | list[string] | 当前待办协助人列表                                           |
| `cost_time`           | string       | 单据耗时（展示值）                                           |
| `bk_biz_name`         | string       | 业务名称                                                     |
| `db_app_abbr`         | string       | 业务英文缩写                                                 |
| `create_at`           | string       | 创建时间                                                     |
| `update_at`           | string       | 更新时间                                                     |
| `creator`             | string       | 创建人                                                       |
| `updater`             | string       | 更新人                                                       |

### `details` 系统补充字段说明

#### 副本集（`MONGODB_REPLICASET_APPLY`）

| 字段                                      | 类型         | 说明                                                         |
| ----------------------------------------- | ------------ | ------------------------------------------------------------ |
| `infos`                                   | list[dict]   | 系统根据 `replica_count / node_replica_count` 生成的资源申请分组列表 |
| `infos[].bk_cloud_id`                     | int          | 云区域 ID                                                    |
| `infos[].resource_spec.mongo_machine_set` | dict         | 副本集节点规格（含 `tolerance`、`spec_name` 等系统补充字段） |
| `bk_app_abbr`                             | string       | 由 `db_app_abbr` 转换而来，供后台 flow 使用                  |
| `zone_list`                               | list[string] | 系统根据 `mongo_machine_set` 补充的园区列表                  |

#### 分片集群（`MONGODB_SHARD_APPLY`）

| 字段                                   | 类型         | 说明                                                         |
| -------------------------------------- | ------------ | ------------------------------------------------------------ |
| `resource_spec.mongodb.tolerance`      | float        | 系统根据 `disaster_tolerance_level` 计算的 mongodb 节点容忍度 |
| `resource_spec.mongo_config.tolerance` | float        | 系统根据 `disaster_tolerance_level` 计算的 config 节点容忍度 |
| `resource_spec.mongos.tolerance`       | float        | 系统根据 `disaster_tolerance_level` 计算的 mongos 节点容忍度 |
| `resource_spec.mongodb_nodes_{n}`      | dict         | 系统按 `shard_machine_group` 展开的各组 mongodb 节点规格（n 从 0 开始） |
| `bk_app_abbr`                          | string       | 由 `db_app_abbr` 转换而来，供后台 flow 使用                  |
| `proxy_port`                           | int          | 由 `start_port` 赋值，供 mongos 使用                         |
| `zone_list`                            | list[string] | 系统根据 `mongo_config` 补充的园区列表                       |
| `machine_specs`                        | dict         | 资源申请完成后回填的各角色机器规格信息（含 `spec_id`、`spec_config`） |
| `nodes.mongodb`                        | list[list]   | 资源申请完成后，将 `mongodb_nodes_0`、`mongodb_nodes_1`、... 聚合后的 mongodb 节点列表 |

---

## 常见失败场景

- `replica_sets[].set_id` 或 `domain` 格式不合法或已存在冲突。
- `cluster_name` 格式不合法或已存在同名集群。
- `resource_spec` 中缺少必要的角色规格（分片集群需同时提供 `mongodb`、`mongo_config`、`mongos`）。
- `details` 结构与 `ticket_type` 不匹配，导致动态序列化校验失败。
- `disaster_tolerance_level` 为 `SAME_SUBZONE` 或 `SAME_SUBZONE_CROSS_SWTICH` 时，未在 `location_spec.sub_zone_ids` 中指定园区 ID（副本集场景）。


---

### Kafka 集群部署类单据

### 功能描述

通过 `/apis/tickets/` 创建 **Kafka 集群部署类单据**，并触发后续单据流程（审批/人工确认/资源申请/部署执行）。

---

## 支持的部署单据类型

| ticket_type   | 说明           | 对应 Builder            |
| ------------- | -------------- | ----------------------- |
| `KAFKA_APPLY` | Kafka 集群部署 | `KafkaApplyFlowBuilder` |

---

## 顶层请求参数

| 字段                 | 类型   | 必选 | 描述                                            |
| -------------------- | ------ | ---- | ----------------------------------------------- |
| `bk_biz_id`          | int    | 是   | 业务 ID                                         |
| `ticket_type`        | string | 是   | 单据类型（本场景固定为 `KAFKA_APPLY`）          |
| `details`            | dict   | 是   | 单据详情，按 `ticket_type` 动态选择序列化器校验 |
| `remark`             | string | 否   | 单据备注                                        |
| `ignore_duplication` | bool   | 否   | 是否忽略重复单据校验，默认 `false`              |
| `config`             | dict   | 否   | 单据配置（通知配置、协助人等）                  |

---

## `details` 参数定义

### `KAFKA_APPLY`（Kafka 集群部署）

序列化器：`KafkaApplyDetailSerializer`（继承自 `BigDataApplyDetailsSerializer`）

| 字段                       | 类型   | 必选     | 描述                                                         |
| -------------------------- | ------ | -------- | ------------------------------------------------------------ |
| `bk_cloud_id`              | int    | 是       | 云区域 ID                                                    |
| `db_app_abbr`              | string | 是       | 业务英文缩写                                                 |
| `cluster_name`             | string | 是       | 集群名称（用于域名拼接，需满足域名标签规范：英文/数字/中划线 `-`，且以英文或数字开头） |
| `cluster_alias`            | string | 否       | 集群别名（一般为中文别名），可为空                           |
| `city_code`                | string | 否       | 城市代码，可空，默认 `""`                                    |
| `disaster_tolerance_level` | string | 否       | 容灾级别，固定为 `MAX_EACH_ZONE_EQUAL`（系统强制覆盖，无需手动传入） |
| `db_version`               | string | 是       | Kafka 版本号（如 `kafka_2.4.0`）                             |
| `port`                     | int    | 否       | Kafka Broker 端口，默认 `9200`                               |
| `replication_num`          | int    | 是       | 副本数量（必须 ≤ Broker 节点数量）                           |
| `partition_num`            | int    | 是       | 分区数量                                                     |
| `retention_hours`          | int    | 是       | 消息保留时长（小时）                                         |
| `retention_bytes`          | int    | 否       | 消息保留大小（字节），默认 `-1`（不限制）                    |
| `no_security`              | int    | 否       | 无认证开关：`0` 表示开启认证（默认），`1` 表示无认证         |
| `ip_source`                | string | 是       | 主机来源：`resource_pool`（资源池）或 `manual_input`（手动录入） |
| `nodes`                    | dict   | 条件必选 | 手动录入时的部署节点，`ip_source = manual_input` 时必填，详见下文 `nodes` 参数定义 |
| `resource_spec`            | dict   | 条件必选 | 资源池申请规格，`ip_source = resource_pool` 时必填，详见下文 `resource_spec` 参数定义 |

### `nodes` 参数定义（`ip_source = manual_input` 时必填）

`nodes` 包含两类角色的主机列表：

| 字段        | 类型 | 必选 | 描述                                                         |
| ----------- | ---- | ---- | ------------------------------------------------------------ |
| `zookeeper` | list | 是   | ZooKeeper 节点列表，**固定为 3 台**                          |
| `broker`    | list | 是   | Broker 节点列表，**至少 1 台**，且数量必须 ≥ `replication_num` |

每个节点元素结构：

| 字段          | 类型   | 必选 | 描述                 |
| ------------- | ------ | ---- | -------------------- |
| `ip`          | string | 是   | 主机 IP              |
| `bk_cloud_id` | int    | 是   | 云区域 ID            |
| `bk_host_id`  | int    | 否   | 主机 ID（来自 CMDB） |

> 校验规则：
>
> - 各角色主机之间**不允许 IP 重复**（角色互斥）。
> - ZooKeeper 节点数量**固定为 3 台**，不可多也不可少。
> - Broker 节点数量**至少为 1 台**，且 `replication_num` 必须 ≤ Broker 节点数量。
> - 所有主机必须来自**空闲机池**，且不能已存在于 DBMeta 中。

### `resource_spec` 参数定义（`ip_source = resource_pool` 时必填）

`resource_spec` 包含两类角色的资源规格：

| 字段        | 类型 | 必选 | 描述                                              |
| ----------- | ---- | ---- | ------------------------------------------------- |
| `zookeeper` | dict | 是   | ZooKeeper 节点规格，详见下文 `resource_spec_item` |
| `broker`    | dict | 是   | Broker 节点规格，详见下文 `resource_spec_item`    |

#### `resource_spec_item`

| 字段            | 类型 | 必选 | 描述                               |
| --------------- | ---- | ---- | ---------------------------------- |
| `spec_id`       | int  | 是   | 规格 ID                            |
| `count`         | int  | 是   | 申请机器数量                       |
| `location_spec` | dict | 否   | 地域约束，详见下文 `location_spec` |

#### `location_spec`

| 字段           | 类型      | 必选 | 描述                |
| -------------- | --------- | ---- | ------------------- |
| `city`         | string    | 否   | 城市代码（如 `sz`） |
| `sub_zone_ids` | list[int] | 否   | 园区 ID 列表        |

> 说明：
>
> - 资源池模式下，系统会自动为每个角色的 `resource_spec` 补充 `affinity = MAX_EACH_ZONE_EQUAL`（大数据组件固定亲和性策略）。
> - `zookeeper.count` 必须为 `3`，`broker.count` 必须 ≥ `replication_num`。
> - `resource_spec` 中无用的角色规格（`count = 0` 或未提供）会被系统自动移除。

---

## 请求示例

### 示例一：资源池模式部署

```json
{
  "bk_biz_id": 3,
  "ticket_type": "KAFKA_APPLY",
  "remark": "Kafka集群部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "cluster_name": "kafka-game-log",
    "cluster_alias": "游戏日志Kafka集群",
    "city_code": "sz",
    "db_version": "kafka_2.4.0",
    "port": 9200,
    "replication_num": 2,
    "partition_num": 4,
    "retention_hours": 168,
    "retention_bytes": -1,
    "no_security": 0,
    "ip_source": "resource_pool",
    "resource_spec": {
      "zookeeper": {
        "spec_id": 3001,
        "count": 3,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "broker": {
        "spec_id": 3002,
        "count": 3,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    }
  }
}
```

### 示例二：手动录入模式部署

```json
{
  "bk_biz_id": 3,
  "ticket_type": "KAFKA_APPLY",
  "remark": "Kafka集群手动部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "cluster_name": "kafka-game-event",
    "cluster_alias": "游戏事件Kafka集群",
    "city_code": "sz",
    "db_version": "kafka_2.4.0",
    "port": 9200,
    "replication_num": 2,
    "partition_num": 4,
    "retention_hours": 72,
    "retention_bytes": -1,
    "no_security": 0,
    "ip_source": "manual_input",
    "nodes": {
      "zookeeper": [
        {"ip": "0.0.0.0", "bk_cloud_id": 0, "bk_host_id": 1001},
        {"ip": "0.0.0.0", "bk_cloud_id": 0, "bk_host_id": 1002},
        {"ip": "0.0.0.0", "bk_cloud_id": 0, "bk_host_id": 1003}
      ],
      "broker": [
        {"ip": "0.0.0.0", "bk_cloud_id": 0, "bk_host_id": 1004},
        {"ip": "0.0.0.0", "bk_cloud_id": 0, "bk_host_id": 1005},
        {"ip": "0.0.0.0", "bk_cloud_id": 0, "bk_host_id": 1006}
      ]
    }
  }
}
```

---

## 返回结果示例

```json
{
  "id": 3001,
  "bk_biz_id": 3,
  "group": "kafka",
  "ticket_type": "KAFKA_APPLY",
  "ticket_type_display": "Kafka 集群部署",
  "status": "PENDING",
  "status_display": "待审批",
  "remark": "Kafka集群部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "cluster_name": "kafka-game-log",
    "cluster_alias": "游戏日志Kafka集群",
    "city_code": "sz",
    "disaster_tolerance_level": "MAX_EACH_ZONE_EQUAL",
    "db_version": "kafka_2.4.0",
    "port": 9200,
    "replication_num": 2,
    "partition_num": 4,
    "retention_hours": 168,
    "retention_bytes": -1,
    "no_security": 0,
    "ip_source": "resource_pool",
    "resource_spec": {
      "zookeeper": {
        "spec_id": 3001,
        "count": 3,
        "affinity": "MAX_EACH_ZONE_EQUAL",
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "broker": {
        "spec_id": 3002,
        "count": 3,
        "affinity": "MAX_EACH_ZONE_EQUAL",
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    },
    "bk_cloud_name": "直连区域",
    "city_name": "深圳"
  },
  "todo_operators": [],
  "todo_helpers": [],
  "cost_time": "2s",
  "bk_biz_name": "DBA测试业务",
  "db_app_abbr": "game",
  "create_at": "2026-03-17T16:00:00+08:00",
  "update_at": "2026-03-17T16:00:02+08:00",
  "creator": "admin",
  "updater": "admin"
}
```

---

## 返回结果字段说明

接口返回 `TicketSerializer` 序列化后的单据对象。

### 顶层字段

| 字段                  | 类型         | 说明                                                       |
| --------------------- | ------------ | ---------------------------------------------------------- |
| `id`                  | int          | 单据 ID                                                    |
| `bk_biz_id`           | int          | 业务 ID                                                    |
| `group`               | string       | 单据分组（Kafka 为 `kafka`）                               |
| `ticket_type`         | string       | 单据类型（`KAFKA_APPLY`）                                  |
| `ticket_type_display` | string       | 单据类型展示名                                             |
| `status`              | string       | 单据状态（如 `PENDING`、`RUNNING`、`SUCCEEDED`、`FAILED`） |
| `status_display`      | string       | 单据状态展示名                                             |
| `remark`              | string       | 单据备注                                                   |
| `ignore_duplication`  | bool         | 是否忽略重复校验                                           |
| `details`             | dict         | 单据详情（含提交参数及系统补充字段）                       |
| `todo_operators`      | list[string] | 当前待办处理人列表                                         |
| `todo_helpers`        | list[string] | 当前待办协助人列表                                         |
| `cost_time`           | string       | 单据耗时（展示值）                                         |
| `bk_biz_name`         | string       | 业务名称                                                   |
| `db_app_abbr`         | string       | 业务英文缩写                                               |
| `create_at`           | string       | 创建时间                                                   |
| `update_at`           | string       | 更新时间                                                   |
| `creator`             | string       | 创建人                                                     |
| `updater`             | string       | 更新人                                                     |

### `details` 字段说明

| 字段                       | 类型   | 说明                                                        |
| -------------------------- | ------ | ----------------------------------------------------------- |
| `bk_cloud_id`              | int    | 云区域 ID                                                   |
| `db_app_abbr`              | string | 业务英文缩写                                                |
| `cluster_name`             | string | 集群名称                                                    |
| `cluster_alias`            | string | 集群别名                                                    |
| `city_code`                | string | 城市代码                                                    |
| `disaster_tolerance_level` | string | 容灾级别（固定为 `MAX_EACH_ZONE_EQUAL`）                    |
| `db_version`               | string | Kafka 版本号                                                |
| `port`                     | int    | Kafka Broker 端口                                           |
| `replication_num`          | int    | 副本数量                                                    |
| `partition_num`            | int    | 分区数量                                                    |
| `retention_hours`          | int    | 消息保留时长（小时）                                        |
| `retention_bytes`          | int    | 消息保留大小（字节），`-1` 表示不限制                       |
| `no_security`              | int    | 无认证开关（`0` 认证，`1` 无认证）                          |
| `ip_source`                | string | 主机来源                                                    |
| `resource_spec`            | dict   | 资源规格（资源池模式，含 `zookeeper`、`broker` 两个角色）   |
| `nodes`                    | dict   | 部署节点（手动录入模式，含 `zookeeper`、`broker` 两个角色） |
| `bk_cloud_name`            | string | 展示字段：云区域名称                                        |
| `city_name`                | string | 展示字段：城市名称                                          |

### `details.resource_spec` 系统补充字段说明

| 字段路径                                | 类型   | 说明                                   |
| --------------------------------------- | ------ | -------------------------------------- |
| `resource_spec.zookeeper.affinity`      | string | 系统补充：固定为 `MAX_EACH_ZONE_EQUAL` |
| `resource_spec.zookeeper.location_spec` | dict   | 地域约束（城市 + 园区）                |
| `resource_spec.broker.affinity`         | string | 系统补充：固定为 `MAX_EACH_ZONE_EQUAL` |
| `resource_spec.broker.location_spec`    | dict   | 地域约束（城市 + 园区）                |

> 说明：
>
> - 创建接口返回的 `details` 以提单参数与序列化展示字段为主（如 `bk_cloud_name`、`city_name`）。
> - Kafka 流程执行阶段会使用 `username/password/domain` 等内部参数，但这些字段**不应作为创建接口返回的固定字段依赖**。

---

## 常见失败场景

- `cluster_name` 格式不合法或同业务下已存在同名同类型集群。
- `zookeeper` 节点数量不等于 3 台。
- `broker` 节点数量少于 1 台，或 `replication_num` 大于 `broker` 节点数量。
- 手动录入模式下，不同角色的主机 IP 出现重复（角色互斥）。
- 手动录入模式下，主机不在空闲机池中，或已存在于 DBMeta 中。
- `resource_spec` 中缺少 `zookeeper` 或 `broker` 角色规格（资源池模式）。
- `details` 结构与 `ticket_type` 不匹配，导致动态序列化校验失败。


---

###  Redis 集群部署类单据

### 功能描述

通过 `/apis/tickets/` 创建 **Redis 集群部署类单据**，并触发后续单据流程（审批/人工确认/资源申请/部署执行）。

---

## 支持的部署单据类型

| ticket_type           | 说明                                                         | 对应 Builder                                                 |
| --------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `REDIS_CLUSTER_APPLY` | Redis 集群部署（含 TendisCache / TendisSSD / RedisCluster / Tendisplus） | `RedisClusterApplyFlowBuilder`                               |
| `REDIS_INS_APPLY`     | Redis 主从节点部署                                           | `RedisClusterApplyFlowBuilder`（`RedisInstanceApplyFlowParamBuilder`） |

---

## 顶层请求参数

| 字段                 | 类型   | 必选 | 描述                                                         |
| -------------------- | ------ | ---- | ------------------------------------------------------------ |
| `bk_biz_id`          | int    | 是   | 业务 ID                                                      |
| `ticket_type`        | string | 是   | 单据类型（本场景为 `REDIS_CLUSTER_APPLY` 或 `REDIS_INS_APPLY`） |
| `details`            | dict   | 是   | 单据详情，按 `ticket_type` 动态选择序列化器校验              |
| `remark`             | string | 否   | 单据备注                                                     |
| `ignore_duplication` | bool   | 否   | 是否忽略重复单据校验，默认 `false`                           |
| `config`             | dict   | 否   | 单据配置（通知配置、协助人等）                               |

---

## `details` 参数定义

### `REDIS_CLUSTER_APPLY`（Redis 集群部署）

序列化器：`RedisClusterApplyDetailSerializer`

支持以下集群类型（通过 `cluster_type` 字段区分）：

| cluster_type 值              | 说明                                          |
| ---------------------------- | --------------------------------------------- |
| `TwemproxyRedisInstance`     | TendisCache 集群（Twemproxy + Redis）         |
| `TwemproxyTendisSSDInstance` | TendisSSD 集群（Twemproxy + TendisSSD）       |
| `PredixyRedisCluster`        | RedisCluster 集群（Predixy + Redis Cluster）  |
| `PredixyTendisplusCluster`   | Tendisplus 存储版集群（Predixy + Tendisplus） |

| 字段                       | 类型   | 必选     | 描述                                                         |
| -------------------------- | ------ | -------- | ------------------------------------------------------------ |
| `bk_cloud_id`              | int    | 是       | 云区域 ID                                                    |
| `db_app_abbr`              | string | 是       | 业务英文缩写                                                 |
| `cluster_name`             | string | 是       | 集群名称（英文、数字及下划线）                               |
| `cluster_alias`            | string | 否       | 集群别名（一般为中文别名），可为空                           |
| `cluster_type`             | string | 是       | 集群类型，见上表                                             |
| `db_version`               | string | 是       | 版本号（如 `Redis-6`）                                       |
| `proxy_port`               | int    | 是       | 集群接入层端口                                               |
| `proxy_pwd`                | string | 否       | Proxy 访问密码（不传则系统随机生成，传入则校验密码强度）     |
| `city_code`                | string | 否       | 城市代码，可空，默认 `""`                                    |
| `disaster_tolerance_level` | string | 否       | 容灾级别，默认 `NONE`，可选值见下文                          |
| `cluster_shard_num`        | int    | 是       | 集群分片数（`PredixyRedisCluster` / `PredixyTendisplusCluster` 类型要求 ≥ 3） |
| `ip_source`                | string | 是       | 主机来源：`resource_pool`（资源池）                          |
| `resource_spec`            | dict   | 条件必选 | 资源池申请规格，`ip_source = resource_pool` 时必填，详见下文 `resource_spec` 参数定义 |

#### 容灾级别（`disaster_tolerance_level`）可选值

| 值                          | 说明                      |
| --------------------------- | ------------------------- |
| `NONE`                      | 无（默认）                |
| `SAME_SUBZONE_CROSS_SWTICH` | 指定园区                  |
| `SAME_SUBZONE`              | 指定园区（无机架要求）    |
| `CROS_SUBZONE`              | 跨园区                    |
| `CROSS_RACK`                | 不限园区                  |
| `MAX_EACH_ZONE_EQUAL`       | 每个 subzone 尽量均匀分布 |

### `resource_spec` 参数定义（`ip_source = resource_pool` 时必填）

`resource_spec` 包含两类角色的资源规格：

| 字段            | 类型 | 必选 | 描述                                              |
| --------------- | ---- | ---- | ------------------------------------------------- |
| `proxy`         | dict | 是   | Proxy 节点规格，详见下文 `resource_spec_item`     |
| `backend_group` | dict | 是   | 后端主从节点组规格，详见下文 `resource_spec_item` |

#### `resource_spec_item`

| 字段            | 类型 | 必选 | 描述                                                         |
| --------------- | ---- | ---- | ------------------------------------------------------------ |
| `spec_id`       | int  | 是   | 规格 ID                                                      |
| `count`         | int  | 是   | 申请机器数量（`backend_group.count` 表示机器组数，每组含 1 master + 1 slave） |
| `location_spec` | dict | 否   | 地域约束，详见下文 `location_spec`                           |

#### `location_spec`

| 字段           | 类型      | 必选 | 描述                |
| -------------- | --------- | ---- | ------------------- |
| `city`         | string    | 否   | 城市代码（如 `sz`） |
| `sub_zone_ids` | list[int] | 否   | 园区 ID 列表        |

> 说明：
>
> - 资源池模式下，系统会自动为 `proxy` 的 `resource_spec` 补充 `group_count = 2`（接入层 Proxy 要求至少分布在 2 个机房）。
> - `backend_group.count` 表示机器组数，每组包含 1 台 master 和 1 台 slave。
> - 资源申请完成后（`post_callback`），系统会根据实际分配的机器内存/磁盘自动计算并补充 `maxmemory`、`max_disk`、`group_num`、`shard_num` 等字段。

---

### `REDIS_INS_APPLY`（Redis 主从节点部署）

序列化器：`RedisInstanceApplyDetailSerializer`（继承自 `RedisBaseOperateDetailSerializer`）

| 字段                       | 类型   | 必选 | 描述                                                       |
| -------------------------- | ------ | ---- | ---------------------------------------------------------- |
| `bk_cloud_id`              | int    | 是   | 云区域 ID                                                  |
| `db_app_abbr`              | string | 是   | 业务英文缩写                                               |
| `cluster_type`             | string | 是   | 集群类型（建议使用 `RedisInstance`，即 RedisCache 主从版） |
| `db_version`               | string | 否   | 版本号（如 `Redis-6`）                                     |
| `port`                     | int    | 否   | 集群起始端口                                               |
| `redis_pwd`                | string | 否   | 访问密码（不传则系统随机生成）                             |
| `city_code`                | string | 否   | 城市代码                                                   |
| `disaster_tolerance_level` | string | 否   | 容灾级别，默认 `NONE`                                      |

| `append_apply` | bool | 是 | 是否为追加部署（`false` 为新建，`true` 为追加到已有机器） |
| `ip_source` | string | 否 | 主机来源，默认 `resource_pool` |
| `infos` | list | 是 | 集群信息列表，每个元素代表一个主从集群，详见下文 `infos` 参数定义 |
| `resource_spec` | dict | 条件必选 | 新建部署（`append_apply = false`）时必填；追加部署时通常由 `infos[].backend_group` 提供目标主机，详见下文 |
| `nodes` | dict | 否 | 预留字段（当前 `REDIS_INS_APPLY` 的核心流程不依赖该字段） |

#### `infos` 参数定义

| 字段            | 类型   | 必选     | 描述                                                |
| --------------- | ------ | -------- | --------------------------------------------------- |
| `cluster_name`  | string | 是       | 集群名称（英文、数字及下划线）                      |
| `databases`     | int    | 是       | DB 数量                                             |
| `backend_group` | dict   | 条件必选 | 追加部署时必填，包含 `master` 和 `slave` 的主机信息 |

#### `resource_spec` 参数定义（`REDIS_INS_APPLY` 新建部署时必填）

| 字段            | 类型 | 必选 | 描述                                        |
| --------------- | ---- | ---- | ------------------------------------------- |
| `backend_group` | dict | 是   | 后端主从节点组规格（`spec_id` + `count`）   |
| `master`        | dict | 否   | master 规格（资源申请后回填到每个 info 中） |

> 校验规则：
>
> - 新建部署时，`resource_spec.backend_group.count`（机器组数）必须能整除 `infos` 的集群数量。
> - 追加部署时，`infos[].backend_group` 中需提供已有机器的 `master.bk_host_id`，系统会自动查找该机器上的最大端口并递增分配。

---

## 系统自动补充字段说明

### `REDIS_CLUSTER_APPLY` 系统补充字段（`format_ticket_data`）

| 字段              | 类型   | 说明                                                         |
| ----------------- | ------ | ------------------------------------------------------------ |
| `proxy_pwd`       | string | Proxy 访问密码（用户未传入时随机生成，符合 `REDIS_PASSWORD` 安全策略） |
| `proxy_admin_pwd` | string | Proxy 管理密码（系统随机生成）                               |
| `redis_pwd`       | string | Redis 访问密码（系统随机生成；`PredixyRedisCluster` / `PredixyTendisplusCluster` 类型与 `proxy_pwd` 相同） |
| `domain_name`     | string | 集群访问域名，格式见下表                                     |
| `databases`       | int    | 库数量，固定为 `2`                                           |
| `city`            | string | 城市代码（同 `city_code`）                                   |
| `zone_list`       | list   | 可用区列表（资源池模式且容灾级别为指定/跨园区时，来自 `resource_spec.backend_group.location_spec.sub_zone_ids`；其他场景可能为空） |

#### 域名生成规则（`domain_name`）

| cluster_type                 | 域名前缀       | 域名格式                                       |
| ---------------------------- | -------------- | ---------------------------------------------- |
| `TwemproxyRedisInstance`     | `cache`        | `cache.{cluster_name}.{db_app_abbr}.db`        |
| `TwemproxyTendisSSDInstance` | `ssd`          | `ssd.{cluster_name}.{db_app_abbr}.db`          |
| `PredixyRedisCluster`        | `rediscluster` | `rediscluster.{cluster_name}.{db_app_abbr}.db` |
| `PredixyTendisplusCluster`   | `tendisplus`   | `tendisplus.{cluster_name}.{db_app_abbr}.db`   |

#### 资源申请后系统补充字段（`post_callback`）

| 字段        | 类型 | 说明                                                         |
| ----------- | ---- | ------------------------------------------------------------ |
| `maxmemory` | int  | 单分片最大内存（字节），由 `min_mem * group_num / shard_num * 1024 * 1024` 计算得出 |
| `max_disk`  | int  | 单分片最大磁盘（GB），由 `min_disk * group_num / shard_num` 计算得出 |
| `group_num` | int  | 机器组数（来自 `resource_spec.backend_group.count`）         |
| `shard_num` | int  | 分片数（来自 `cluster_shard_num`）                           |

### `REDIS_INS_APPLY` 系统补充字段（`format_ticket_data`）

每个 `infos` 元素会被补充以下字段：

| 字段                       | 类型   | 说明                                                       |
| -------------------------- | ------ | ---------------------------------------------------------- |
| `domain_name`              | string | 集群访问域名，格式为 `ins.{cluster_name}.{db_app_abbr}.db` |
| `redis_pwd`                | string | 访问密码（用户未传入时随机生成）                           |
| `disaster_tolerance_level` | string | 容灾级别（继承自顶层）                                     |
| `city` / `city_code`       | string | 城市代码（继承自顶层）                                     |
| `db_version`               | string | 版本号（继承自顶层）                                       |
| `cluster_alias`            | string | 集群别名（同 `cluster_name`）                              |

> 说明：新建部署时端口按“每个机器组”独立递增分配；当每个机器组仅承载 1 个集群时，不同集群的 `port` 可能相同。

---

## 请求示例

### 示例一：`REDIS_CLUSTER_APPLY` 资源池模式部署（TendisCache 集群）

```json
{
  "bk_biz_id": 3,
  "ticket_type": "REDIS_CLUSTER_APPLY",
  "remark": "TendisCache集群部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "cluster_name": "game-cache-01",
    "cluster_alias": "游戏缓存集群",
    "cluster_type": "TwemproxyRedisInstance",
    "db_version": "Redis-6",
    "proxy_port": 50000,
    "city_code": "sz",
    "disaster_tolerance_level": "NONE",
    "cluster_shard_num": 4,
    "ip_source": "resource_pool",
    "resource_spec": {
      "proxy": {
        "spec_id": 2001,
        "count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "backend_group": {
        "spec_id": 2002,
        "count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    }
  }
}
```

### 示例二：`REDIS_CLUSTER_APPLY` 资源池模式部署（RedisCluster 集群）

```json
{
  "bk_biz_id": 3,
  "ticket_type": "REDIS_CLUSTER_APPLY",
  "remark": "RedisCluster集群部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "cluster_name": "game-rediscluster-01",
    "cluster_alias": "游戏RedisCluster集群",
    "cluster_type": "PredixyRedisCluster",
    "db_version": "Redis-7",
    "proxy_port": 50001,
    "city_code": "sz",
    "disaster_tolerance_level": "NONE",
    "cluster_shard_num": 6,
    "ip_source": "resource_pool",
    "resource_spec": {
      "proxy": {
        "spec_id": 2001,
        "count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "backend_group": {
        "spec_id": 2002,
        "count": 3,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    }
  }
}
```

### 示例三：`REDIS_INS_APPLY` 资源池模式部署（Redis 主从）

```json
{
  "bk_biz_id": 3,
  "ticket_type": "REDIS_INS_APPLY",
  "remark": "Redis主从部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "cluster_type": "RedisInstance",
    "db_version": "Redis-6",
    "port": 30000,
    "city_code": "sz",
    "disaster_tolerance_level": "NONE",
    "append_apply": false,
    "ip_source": "resource_pool",
    "infos": [
      {
        "cluster_name": "game-ins-01",
        "databases": 2
      },
      {
        "cluster_name": "game-ins-02",
        "databases": 2
      }
    ],
    "resource_spec": {
      "backend_group": {
        "spec_id": 2003,
        "count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    }
  }
}
```

---

## 返回结果示例

### `REDIS_CLUSTER_APPLY` 返回示例

```json
{
  "id": 4001,
  "bk_biz_id": 3,
  "group": "redis",
  "ticket_type": "REDIS_CLUSTER_APPLY",
  "ticket_type_display": "Redis 集群部署",
  "status": "PENDING",
  "status_display": "待审批",
  "remark": "TendisCache集群部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "cluster_name": "game-cache-01",
    "cluster_alias": "游戏缓存集群",
    "cluster_type": "TwemproxyRedisInstance",
    "db_version": "Redis-6",
    "proxy_port": 50000,
    "city_code": "sz",
    "disaster_tolerance_level": "NONE",
    "cluster_shard_num": 4,
    "ip_source": "resource_pool",
    "resource_spec": {
      "proxy": {
        "spec_id": 2001,
        "count": 2,
        "group_count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      },
      "backend_group": {
        "spec_id": 2002,
        "count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    },
    "proxy_pwd": "Kf3@xP9mQz",
    "proxy_admin_pwd": "Lm7#nR2wYv",
    "redis_pwd": "Pq5!sT8uXb",
    "domain_name": "cache.game-cache-01.game.db",
    "databases": 2,
    "city": "sz",
    "zone_list": [],
    "maxmemory": 3221225472,
    "max_disk": 100,
    "group_num": 2,
    "shard_num": 4,
    "bk_cloud_name": "直连区域",
    "city_name": "深圳"


  },
  "todo_operators": [],
  "todo_helpers": [],
  "cost_time": "3s",
  "bk_biz_name": "DBA测试业务",
  "db_app_abbr": "game",
  "create_at": "2026-03-17T17:00:00+08:00",
  "update_at": "2026-03-17T17:00:03+08:00",
  "creator": "admin",
  "updater": "admin"
}
```

### `REDIS_INS_APPLY` 返回示例

```json
{
  "id": 4002,
  "bk_biz_id": 3,
  "group": "redis",
  "ticket_type": "REDIS_INS_APPLY",
  "ticket_type_display": "Redis 主从节点部署",
  "status": "PENDING",
  "status_display": "待审批",
  "remark": "Redis主从部署",
  "ignore_duplication": false,
  "details": {
    "bk_cloud_id": 0,
    "db_app_abbr": "game",
    "cluster_type": "RedisInstance",
    "db_version": "Redis-6",
    "port": 30000,
    "city_code": "sz",
    "disaster_tolerance_level": "NONE",
    "append_apply": false,
    "ip_source": "resource_pool",
    "infos": [
      {
        "cluster_name": "game-ins-01",
        "databases": 2,
        "domain_name": "ins.game-ins-01.game.db",
        "redis_pwd": "Pq5!sT8uXb",
        "disaster_tolerance_level": "NONE",
        "city": "sz",
        "city_code": "sz",
        "db_version": "Redis-6",
        "cluster_alias": "game-ins-01",
        "port": 30000,
        "maxmemory": 1610612736
      },
      {
        "cluster_name": "game-ins-02",
        "databases": 2,
        "domain_name": "ins.game-ins-02.game.db",
        "redis_pwd": "Pq5!sT8uXb",
        "disaster_tolerance_level": "NONE",
        "city": "sz",
        "city_code": "sz",
        "db_version": "Redis-6",
        "cluster_alias": "game-ins-02",
        "port": 30000,
        "maxmemory": 1610612736
      }
    ],

    "resource_spec": {
      "backend_group": {
        "spec_id": 2003,
        "count": 2,
        "location_spec": {
          "city": "sz",
          "sub_zone_ids": []
        }
      }
    },
    "zone_list": [],
    "bk_cloud_name": "直连区域",
    "city_name": "深圳"

  },
  "todo_operators": [],

  "todo_helpers": [],
  "cost_time": "2s",
  "bk_biz_name": "DBA测试业务",
  "db_app_abbr": "game",
  "create_at": "2026-03-17T17:00:00+08:00",
  "update_at": "2026-03-17T17:00:02+08:00",
  "creator": "admin",
  "updater": "admin"
}
```

---

## 返回结果字段说明

接口返回 `TicketSerializer` 序列化后的单据对象。

### 顶层字段

| 字段                  | 类型         | 说明                                                       |
| --------------------- | ------------ | ---------------------------------------------------------- |
| `id`                  | int          | 单据 ID                                                    |
| `bk_biz_id`           | int          | 业务 ID                                                    |
| `group`               | string       | 单据分组（Redis 为 `redis`）                               |
| `ticket_type`         | string       | 单据类型（`REDIS_CLUSTER_APPLY` 或 `REDIS_INS_APPLY`）     |
| `ticket_type_display` | string       | 单据类型展示名                                             |
| `status`              | string       | 单据状态（如 `PENDING`、`RUNNING`、`SUCCEEDED`、`FAILED`） |
| `status_display`      | string       | 单据状态展示名                                             |
| `remark`              | string       | 单据备注                                                   |
| `ignore_duplication`  | bool         | 是否忽略重复校验                                           |
| `details`             | dict         | 单据详情（含提交参数及系统补充字段）                       |
| `todo_operators`      | list[string] | 当前待办处理人列表                                         |
| `todo_helpers`        | list[string] | 当前待办协助人列表                                         |
| `cost_time`           | string       | 单据耗时（展示值）                                         |
| `bk_biz_name`         | string       | 业务名称                                                   |
| `db_app_abbr`         | string       | 业务英文缩写                                               |
| `create_at`           | string       | 创建时间                                                   |
| `update_at`           | string       | 更新时间                                                   |
| `creator`             | string       | 创建人                                                     |
| `updater`             | string       | 更新人                                                     |

### `details` 字段说明（`REDIS_CLUSTER_APPLY`）

| 字段                       | 类型   | 说明                                                    |
| -------------------------- | ------ | ------------------------------------------------------- |
| `bk_cloud_id`              | int    | 云区域 ID                                               |
| `db_app_abbr`              | string | 业务英文缩写                                            |
| `cluster_name`             | string | 集群名称                                                |
| `cluster_alias`            | string | 集群别名                                                |
| `cluster_type`             | string | 集群类型                                                |
| `db_version`               | string | 版本号                                                  |
| `proxy_port`               | int    | 集群接入层端口                                          |
| `proxy_pwd`                | string | Proxy 访问密码（系统补充或用户传入）                    |
| `proxy_admin_pwd`          | string | Proxy 管理密码（系统随机生成）                          |
| `redis_pwd`                | string | Redis 访问密码（系统随机生成）                          |
| `domain_name`              | string | 集群访问域名（系统补充）                                |
| `databases`                | int    | 库数量（固定为 `2`）                                    |
| `city_code`                | string | 城市代码                                                |
| `city`                     | string | 城市代码（同 `city_code`，系统补充）                    |
| `disaster_tolerance_level` | string | 容灾级别                                                |
| `cluster_shard_num`        | int    | 集群分片数                                              |
| `ip_source`                | string | 主机来源                                                |
| `resource_spec`            | dict   | 资源规格（含 `proxy`、`backend_group` 两个角色）        |
| `maxmemory`                | int    | 单分片最大内存（字节，资源申请后系统补充）              |
| `max_disk`                 | int    | 单分片最大磁盘（GB，资源申请后系统补充）                |
| `group_num`                | int    | 机器组数（资源申请后系统补充）                          |
| `shard_num`                | int    | 分片数（资源申请后系统补充）                            |
| `zone_list`                | list   | 可用区列表（资源池模式且容灾级别为指定/跨园区时会回填） |
| `bk_cloud_name`            | string | 展示字段：云区域名称                                    |
| `city_name`                | string | 展示字段：城市名称                                      |
| `cap_spec`                 | string | 展示字段：申请容量详情（同 `cap_key`）                  |

### `details.resource_spec` 系统补充字段说明（`REDIS_CLUSTER_APPLY`）

| 字段路径                                    | 类型 | 说明                                                  |
| ------------------------------------------- | ---- | ----------------------------------------------------- |
| `resource_spec.proxy.group_count`           | int  | 系统补充：固定为 `2`（Proxy 要求至少分布在 2 个机房） |
| `resource_spec.proxy.location_spec`         | dict | 地域约束（城市 + 园区）                               |
| `resource_spec.backend_group.count`         | int  | 机器组数（每组含 1 master + 1 slave）                 |
| `resource_spec.backend_group.location_spec` | dict | 地域约束（城市 + 园区）                               |

### `details` 字段说明（`REDIS_INS_APPLY`）

| 字段                       | 类型       | 说明                                                         |
| -------------------------- | ---------- | ------------------------------------------------------------ |
| `bk_cloud_id`              | int        | 云区域 ID                                                    |
| `db_app_abbr`              | string     | 业务英文缩写                                                 |
| `cluster_type`             | string     | 集群类型（`RedisInstance`）                                  |
| `db_version`               | string     | 版本号                                                       |
| `port`                     | int        | 集群起始端口                                                 |
| `city_code`                | string     | 城市代码                                                     |
| `disaster_tolerance_level` | string     | 容灾级别                                                     |
| `append_apply`             | bool       | 是否为追加部署                                               |
| `ip_source`                | string     | 主机来源                                                     |
| `infos`                    | list[dict] | 集群信息列表（含系统补充的 `domain_name`、`redis_pwd`、`port`、`maxmemory` 等字段） |
| `resource_spec`            | dict       | 资源规格（含 `backend_group` 角色）                          |
| `zone_list`                | list       | 可用区列表（资源池模式且容灾级别为指定/跨园区时会回填）      |
| `bk_cloud_name`            | string     | 展示字段：云区域名称                                         |
| `city_name`                | string     | 展示字段：城市名称                                           |

---

## 常见失败场景

- `cluster_name` 格式不合法或同业务下已存在同名同类型集群。
- `cluster_type` 为 `PredixyRedisCluster` 或 `PredixyTendisplusCluster` 时，`cluster_shard_num` 小于 3。
- 手动录入模式下，`master`、`slave`、`proxy` 三类角色存在重复 IP（角色互斥）。
- 手动录入模式下，`master` 与 `slave` 节点数量不一致，或 `proxy` 节点数量少于 2 台。
- 手动录入模式下，主机不在空闲机池中，或已存在于 DBMeta 中。
- `proxy_pwd` 用户传入但密码强度不符合 `REDIS_PASSWORD` 安全策略。
- `REDIS_INS_APPLY` 新建部署时，`resource_spec.backend_group.count`（机器组数）不能整除 `infos` 的集群数量。
- `details` 结构与 `ticket_type` 不匹配，导致动态序列化校验失败。