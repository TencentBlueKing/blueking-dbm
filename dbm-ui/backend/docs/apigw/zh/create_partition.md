### 功能描述

创建分区配置

### 请求参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| cluster_id   | string | 是 |  集群ID    |
| dblikes   | list[string]  | 是 | 匹配库列表(支持通配) |
| tblikes  | list[string] | 是 | 匹配表列表(不支持通配) |
| partition_column  | string | 是     | 分区字段 |
| partition_column_type | string | 是     | 分区字段类型 |
| expire_time | integer | 是 | 过期时间 |
| partition_time_interval | integer | 是 | 分区间隔 |
| need_dry_run | boolean | 否 | 是否需要获取分区执行数据，默认为true |
| auto_commit | boolean | 否 | 是否自动执行分区，默认为false。若此参数为true，则need_dry_run也要同时为true |

### 请求参数示例(仅获取执行数据)
```json
{
    "bk_biz_id":100465,
    "cluster_id":133,
    "dblikes":["db_worldsvr_example"],
    "tblikes":["mail_box"],
    "partition_column":"ID",
    "partition_column_type":"int",
    "expire_time":3,
    "partition_time_interval":1
}
```

### 返回结果示例(仅获取执行数据)
```json
{
    "data": {
        "4": [
            {
                "ip": "127.0.0.1",
                "port": 20000,
                "shard_name": "SPT0",
                "execute_objects": [
                    {
                        "config_id": 4,
                        "dblike": "db_worldsvr_example_0",
                        "tblike": "mail_box",
                        "init_partition": [
                            {
                                "sql": " D=db_worldsvr_example_0,t=mail_box --alter \"partition by RANGE (ID) ( partition p20240215 values less than (20240215), partition p20240216 values less than (20240216), partition p20240217 values less than (20240217), partition p20240218 values less than (20240218), partition p20240219 values less than (20240219), partition p20240220 values less than (20240220), partition p20240221 values less than (20240221), partition p20240222 values less than (20240222), partition p20240223 values less than (20240223), partition p20240224 values less than (20240224), partition p20240225 values less than (20240225), partition p20240226 values less than (20240226), partition p20240227 values less than (20240227), partition p20240228 values less than (20240228), partition p20240229 values less than (20240229), partition p20240301 values less than (20240301), partition p20240302 values less than (20240302), partition p20240303 values less than (20240303))\" --charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=80 --critical-load=Threads_running=0 --set-vars lock_wait_timeout=5 --print --pause-file=/tmp/partition_osc_pause_db_worldsvr_example_0_mail_box --execute ",
                                "need_size": 196608
                            }
                        ],
                        "add_partition": [],
                        "drop_partition": []
                    }
                ],
                "message": ""
            },
            {
                "ip": "127.0.0.1",
                "port": 20001,
                "shard_name": "SPT1",
                "execute_objects": [
                    {
                        "config_id": 4,
                        "dblike": "db_worldsvr_example_1",
                        "tblike": "mail_box",
                        "init_partition": [
                            {
                                "sql": " D=db_worldsvr_example_1,t=mail_box --alter \"partition by RANGE (ID) ( partition p20240215 values less than (20240215), partition p20240216 values less than (20240216), partition p20240217 values less than (20240217), partition p20240218 values less than (20240218), partition p20240219 values less than (20240219), partition p20240220 values less than (20240220), partition p20240221 values less than (20240221), partition p20240222 values less than (20240222), partition p20240223 values less than (20240223), partition p20240224 values less than (20240224), partition p20240225 values less than (20240225), partition p20240226 values less than (20240226), partition p20240227 values less than (20240227), partition p20240228 values less than (20240228), partition p20240229 values less than (20240229), partition p20240301 values less than (20240301), partition p20240302 values less than (20240302), partition p20240303 values less than (20240303))\" --charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=80 --critical-load=Threads_running=0 --set-vars lock_wait_timeout=5 --print --pause-file=/tmp/partition_osc_pause_db_worldsvr_example_1_mail_box --execute ",
                                "need_size": 196608
                            }
                        ],
                        "add_partition": [],
                        "drop_partition": []
                    }
                ],
                "message": ""
            },
            {
                "ip": "127.0.0.1",
                "port": 20002,
                "shard_name": "SPT2",
                "execute_objects": [
                    {
                        "config_id": 4,
                        "dblike": "db_worldsvr_example_2",
                        "tblike": "mail_box",
                        "init_partition": [
                            {
                                "sql": " D=db_worldsvr_example_2,t=mail_box --alter \"partition by RANGE (ID) ( partition p20240215 values less than (20240215), partition p20240216 values less than (20240216), partition p20240217 values less than (20240217), partition p20240218 values less than (20240218), partition p20240219 values less than (20240219), partition p20240220 values less than (20240220), partition p20240221 values less than (20240221), partition p20240222 values less than (20240222), partition p20240223 values less than (20240223), partition p20240224 values less than (20240224), partition p20240225 values less than (20240225), partition p20240226 values less than (20240226), partition p20240227 values less than (20240227), partition p20240228 values less than (20240228), partition p20240229 values less than (20240229), partition p20240301 values less than (20240301), partition p20240302 values less than (20240302), partition p20240303 values less than (20240303))\" --charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=80 --critical-load=Threads_running=0 --set-vars lock_wait_timeout=5 --print --pause-file=/tmp/partition_osc_pause_db_worldsvr_example_2_mail_box --execute ",
                                "need_size": 196608
                            }
                        ],
                        "add_partition": [],
                        "drop_partition": []
                    }
                ],
                "message": ""
            },
            {
                "ip": "127.0.0.1",
                "port": 20003,
                "shard_name": "SPT3",
                "execute_objects": [
                    {
                        "config_id": 4,
                        "dblike": "db_worldsvr_example_3",
                        "tblike": "mail_box",
                        "init_partition": [
                            {
                                "sql": " D=db_worldsvr_example_3,t=mail_box --alter \"partition by RANGE (ID) ( partition p20240215 values less than (20240215), partition p20240216 values less than (20240216), partition p20240217 values less than (20240217), partition p20240218 values less than (20240218), partition p20240219 values less than (20240219), partition p20240220 values less than (20240220), partition p20240221 values less than (20240221), partition p20240222 values less than (20240222), partition p20240223 values less than (20240223), partition p20240224 values less than (20240224), partition p20240225 values less than (20240225), partition p20240226 values less than (20240226), partition p20240227 values less than (20240227), partition p20240228 values less than (20240228), partition p20240229 values less than (20240229), partition p20240301 values less than (20240301), partition p20240302 values less than (20240302), partition p20240303 values less than (20240303))\" --charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=80 --critical-load=Threads_running=0 --set-vars lock_wait_timeout=5 --print --pause-file=/tmp/partition_osc_pause_db_worldsvr_example_3_mail_box --execute ",
                                "need_size": 196608
                            }
                        ],
                        "add_partition": [],
                        "drop_partition": []
                    }
                ],
                "message": ""
            },
            {
                "ip": "127.0.0.1",
                "port": 26000,
                "shard_name": "TDBCTL0",
                "execute_objects": [
                    {
                        "config_id": 4,
                        "dblike": "db_worldsvr_example",
                        "tblike": "mail_box",
                        "init_partition": [
                            {
                                "sql": "alter table `db_worldsvr_example`.`mail_box` partition by RANGE (ID) ( partition p20240215 values less than (20240215), partition p20240216 values less than (20240216), partition p20240217 values less than (20240217), partition p20240218 values less than (20240218), partition p20240219 values less than (20240219), partition p20240220 values less than (20240220), partition p20240221 values less than (20240221), partition p20240222 values less than (20240222), partition p20240223 values less than (20240223), partition p20240224 values less than (20240224), partition p20240225 values less than (20240225), partition p20240226 values less than (20240226), partition p20240227 values less than (20240227), partition p20240228 values less than (20240228), partition p20240229 values less than (20240229), partition p20240301 values less than (20240301), partition p20240302 values less than (20240302), partition p20240303 values less than (20240303))",
                                "need_size": 0
                            }
                        ],
                        "add_partition": [],
                        "drop_partition": []
                    }
                ],
                "message": ""
            }
        ]
    },
    "code": 0,
    "message": "OK",
    "request_id": "e758b7b7e8bb4d5b8ae8c8f35a5a8c9e"
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| ip | string | 目标实例ip |
| port | 端口 | 目标实例端口 |
| shard_name | string | 目标分片名称（只有TendbCluster会有） |
| execute_objects | list(dict) | 具体执行信息（详见下） |

#### execute_objects参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| config_id | int | 分区配置id |
| dblike | string | 目标库名 |
| tblike | string | 目标表名 |
| init_partition | string | 初始化分区语句 |
| add_partition | string | 添加分区语句 |
| drop_partition | string | 删除分区语句 |             |            |                                |


### 请求参数(创建策略并执行分区)
```json
{
    "bk_biz_id":100465,
    "cluster_id":133,
    "dblikes":["db_worldsvr_example"],
    "tblikes":["mail_box"],
    "partition_column":"ID",
    "partition_column_type":"int",
    "expire_time":3,
    "partition_time_interval":1,
    "need_dry_run": true,
    "auto_commit": true
}
```

### 返回参数(创建策略并执行分区)
```json
[
    {
        "id": 74667,
        "creator": "admin",
        "updater": "admin",
        "bk_biz_id": 5005578,
        "ticket_type": "MYSQL_PARTITION",
        "group": "mysql",
        "status": "PENDING",
        "remark": "分区单据执行",
        "details": {
            "infos": [
                {
                    "config_id": 14368,
                    "cluster_id": 113,
                    "bk_cloud_id": 0,
                    "immute_domain": "make-testdb.xxx-test.xxx.db",
                    "partition_objects": [
                        {
                            "ip": "0.0.0.0",
                            "port": 0,
                            "shard_name": "null",
                            "execute_objects": [
                                {
                                    "config_id": 14368,
                                    "dblike": "kiodb",
                                    "tblike": "table2",
                                    "init_partition": [
                                        {
                                            "sql": " D=kiodb,t=table2 --alter \"partition by RANGE (id) ( partition p20240518 values less than (20240518), partition p20240528 values less than (20240528), partition p20240607 values less than (20240607), partition p20240617 values less than (20240617), partition p20240627 values less than (20240627), partition p20240707 values less than (20240707), partition p20240717 values less than (20240717), partition p20240727 values less than (20240727), partition p20240806 values less than (20240806), partition p20240816 values less than (20240816), partition p20240826 values less than (20240826), partition p20240905 values less than (20240905), partition p20240915 values less than (20240915), partition p20240925 values less than (20240925), partition p20241005 values less than (20241005), partition p20241015 values less than (20241015), partition p20241025 values less than (20241025), partition p20241104 values less than (20241104))\" --charset=utf8 --recursion-method=NONE --alter-foreign-keys-method=auto --max-load Threads_running=80 --critical-load=Threads_running=100 --set-vars lock_wait_timeout=5 --print --pause-file=/tmp/partition_osc_pause_kiodb_table2 --execute ",
                                            "need_size": 49152,
                                            "has_unique_key": true
                                        }
                                    ],
                                    "add_partition": [],
                                    "drop_partition": []
                                }
                            ],
                            "message": ""
                        }
                    ]
                }
            ]
        }
    }
]
```

### 响应参数说明
响应体是一个数组，每个item是一个分区执行单据。一条策略可能生成多个分区单据

| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| id | int | 单据ID |
| creator | string | 创建者 |
| updater | string | 创建者 |
| bk_biz_id | int | 业务ID |
| ticket_type | string | 单据类型 |
| group | string | 所属组件类型 |
| status | string | 单据状态 |
| remark | string | 备注 |
| details | dict | 单据差异化参数 |

在details中，我们只需要关注infos这个key，它是具体策略的执行体，结构是一个数组。
每一项解释如下：

| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| config_id | int | 策略ID |
| cluster_id | int | 集群ID |
| bk_cloud_id | int | 云区域ID |
| immute_domain | string | 集群域名 |
| ticket_type | string | 单据类型 |
| partition_objects | list | 策略执行体。具体解释可以参考上面的execute_objects |