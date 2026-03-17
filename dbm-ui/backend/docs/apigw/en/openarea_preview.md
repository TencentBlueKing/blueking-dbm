### Function Description

Get the preview of zone creation results

### Request Parameters
| Parameter Name | Parameter Type | Required | Description |
| ------------ | ------------ | ------ | ---------------- |
| config_id | int | Yes | Zone creation configuration ID |
| config_data | list(dict) | Yes | Zone creation information (see details below) |

#### config_data Parameters
| Parameter Name | Parameter Type | Required | Description |
| ------------ | ------------ | ------ | ---------------- |
| cluster_id | int | Yes | Target cluster ID |
| authorize_ips | list(string) | Yes | IPs to be authorized in the new zone |
| vars | dict | Yes | Variable set, such as the ID in the target database name paradigm |

### Request Parameters Example
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

### Response Result Example
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
                "operator": "xxxxx",
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
### Response Parameters Description
| Parameter Name | Parameter Type | Description |
| ------------ | ------------ | -------------------------------- |
| config_data | list(dict) | Zone creation configuration information |
| rules_set | list(dict) | Zone creation rule set |