### 功能描述

获取开区模板

### URL请求参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id | int | 是 | 业务ID | 
| cluster_type | string | 是 | 集群类型 | 
| limit | int | 是 | 单页显示条数 | 
| offset | int | 是 | 翻页偏移量 | 

### 返回结果示例
```json
{
    "data": {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 5,
                "creator": "admin",
                "create_at": "2024-01-18T15:58:50+08:00",
                "updater": "admin",
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
                    "region": "上海"
                }
            }
        ]
    },
    "code": 0,
    "message": "OK",
    "request_id": "9285402944cb4ed59b2239dc98e7c2b6"
}
```

### 响应参数results说明
| 参数名称     | 参数类型     | 描述             |
| ------------ | ------------ | ---------------- |
| id | int | 开区配置id |
| creator | string | 开区配置创建者 |
| create_at | string | 开区配置创建时间 |
| updater | string | 开区配置更新者 |
| update_at | string | 开区配置更新时间 |
| config_rules | list（dict） | 开区配置信息（详见下） |
| bk_biz_id | int | 业务ID |
| cluster_type | string | 集群类型 |
| config_name | string | 开区配置名称 |
| source_cluster_id | int | 源集群ID |
| source_cluster | dict | 源集群具体信息（详见下） |

#### config_rules参数说明
| 参数名称     | 参数类型     | 描述             |
| ------------ | ------------ | ---------------- |
| source_db | string | 待克隆数据库 |
| schema_tblist | list(string) | 待克隆表 |
| data_tblist | list(string) | 需要迁移数据的表 |
| target_db_pattern | string | 目标数据库名范式 |
| priv_data | list(int) | 权限模板ID |

#### source_cluster参数说明
| 参数名称     | 参数类型     | 描述             |
| ------------ | ------------ | ---------------- |
| id | int | 源集群ID |
| name | string | 源集群名称 |
| immute_domain | string | 源集群域名 |
| major_version | string | 源集群MySQL版本 |
| bk_cloud_id | int | 源集群资源云区域ID |
| region | string | 源集群资源所在地 |