### Functional Description

Retrieve the open zone template

### URL Request Parameters
| Parameter Name | Parameter Type | Required | Description |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id | int | Yes | Business ID | 
| cluster_type | string | Yes | Cluster type | 
| limit | int | Yes | Number of items per page | 
| offset | int | Yes | Pagination offset | 

### Return Result Example
```json
{
    "data": {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 5,
                "creator": "xxxx",
                "create_at": "2024-01-18T15:58:50+08:00",
                "updater": "xxxx",
                "update_at": "2024-01-18T16:19:24+08:00",
                "config_rules": [
                    {
                        "source_db": "db_worldsvr_example",
                        "schema_tblist": [
                            "tb_1"
                        ],
                        "data_tblist": [
                            "tb_1"
                        ],
                        "target_db_pattern": "db_worldsvr_{id}",
                        "priv_data": [
                            14
                        ]
                    }
                ],
                "bk_biz_id": 100465,
                "cluster_type": "tendbcluster",
                "config_name": "test-tendbcluster",
                "source_cluster_id": 133,
                "source_cluster": {
                    "id": 133,
                    "name": "tengfei-test01",
                    "cluster_type": "tendbcluster",
                    "immute_domain": "spider.tengfei-test01.dbaplatdb.db",
                    "major_version": "MySQL-5.7",
                    "bk_cloud_id": 0,
                    "region": "Shanghai"
                }
            }
        ]
    },
    "code": 0,
    "message": "OK",
    "request_id": "9285402944cb4ed59b2239dc98e7c2b6"
}
```

### Response Parameter `results` Description
| Parameter Name | Parameter Type | Description |
| ------------ | ------------ | ---------------- |
| id | int | Open zone configuration ID |
| creator | string | Creator of the open zone configuration |
| create_at | string | Creation time of the open zone configuration |
| updater | string | Updater of the open zone configuration |
| update_at | string | Update time of the open zone configuration |
| config_rules | list (dict) | Open zone configuration information (see below) |
| bk_biz_id | int | Business ID |
| cluster_type | string | Cluster type |
| config_name | string | Open zone configuration name |
| source_cluster_id | int | Source cluster ID |
| source_cluster | dict | Detailed information of the source cluster (see below) |

#### `config_rules` Parameter Description
| Parameter Name | Parameter Type | Description |
| ------------ | ------------ | ---------------- |
| source_db | string | Database to be cloned |
| schema_tblist | list(string) | Tables to be cloned |
| data_tblist | list(string) | Tables requiring data migration |
| target_db_pattern | string | Target database name pattern |
| priv_data | list(int) | Permission template ID |

#### `source_cluster` Parameter Description
| Parameter Name | Parameter Type | Description |
| ------------ | ------------ | ---------------- |
| id | int | Source cluster ID |
| name | string | Source cluster name |
| immute_domain | string | Domain name of the source cluster |
| major_version | string | MySQL version of the source cluster |
| bk_cloud_id | int | Cloud region ID of the source cluster resources |
| region | string | Location of the source cluster resources |