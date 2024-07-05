### 功能描述

获取开区结果预览

### 请求参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| config_id | int | 是 | 开区配置ID |
| config_data | list(dict) | 是 | 开区信息（详见下）|

#### config_data参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| cluster_id | int | 是 | 目标集群ID |
| authorize_ips | list(string) | 是 | 新区待授权IP |
| vars | dict | 是 | 变量集，如目标数据库名范式中的ID |

### 请求参数示例
```json
{
    "config_id":5,
    "config_data":[
        {
            "cluster_id":133,
            "authorize_ips":["127.0.0.1"],
            "vars":{
                "id":"1002"
            }
        }
    ]
}
```

### 返回结果示例
```json
{
    "data": {
        "config_data": [
            {
                "cluster_id": 133,
                "target_cluster_domain": "spider.tengfei-test01.dbaplatdb.db",
                "execute_objects": [
                    {
                        "source_db": "db_worldsvr_example",
                        "target_db": "db_worldsvr_1002",
                        "schema_tblist": [
                            "tb_1"
                        ],
                        "data_tblist": [
                            "tb_1"
                        ],
                        "priv_data": [
                            14
                        ],
                        "authorize_ips": [
                            "127.0.0.1"
                        ]
                    }
                ]
            }
        ],
        "rules_set": [
            {
                "bk_biz_id": 100465,
                "operator": "admin",
                "user": "test",
                "source_ips": [
                    "127.0.0.1"
                ],
                "target_instances": [
                    "spider.tengfei-test01.dbaplatdb.db"
                ],
                "account_rules": [
                    {
                        "bk_biz_id": 100465,
                        "dbname": "db_worldsvr_%"
                    }
                ],
                "cluster_type": "tendbcluster"
            }
        ]
    },
    "code": 0,
    "message": "OK",
    "request_id": "83afca04f2594b5896bf216fcfb360df"
}
```
### 响应参数说明
| 参数名称     | 参数类型   | 描述  
| ------------ | ------------ |---------------- |
| config_data | list(dict) | 开区配置信息 | 
| rules_set | list(dict) | 开区规则集 |