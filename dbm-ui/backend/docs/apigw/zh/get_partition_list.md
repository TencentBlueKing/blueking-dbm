### 功能描述

获取分区策略列表

### 请求参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id | int | 是 | 业务ID |
| cluster_type | string | 是 | 集群类型 | 
| immute_domains | string | 否 | 集群域名 | 
| dblikes | string | 否 | 匹配库 | 
| tblikes | string | 否 | 匹配表 | 
| limit | int | 否 | 单页展示数（默认10条） | 
| offset | int | 否 | 翻页偏移量 | 

### 返回结果示例
```json
{
    "data": {
        "count": 1,
        "results": [
            {
                "id": 4,
                "bk_biz_id": 100465,
                "immute_domain": "spider.tengfei-test01.dbaplatdb.db",
                "port": 25000,
                "bk_cloud_id": 0,
                "cluster_id": 133,
                "dblike": "db_example",
                "tblike": "tb_1",
                "partition_columns": "ID",
                "partition_column_type": "int",
                "reserved_partition": 3,
                "extra_partition": 15,
                "partition_time_interval": 1,
                "partition_type": 101,
                "expire_time": 3,
                "time_zone": "+08:00",
                "phase": "online",
                "creator": "admin",
                "updator": "admin",
                "create_time": "2024-02-17T08:46:42Z",
                "update_time": "2024-02-17T08:46:42Z",
                "execute_time": "",
                "ticket_id": 0,
                "status": "PENDING",
                "ticket_status": "",
                "check_info": ""
            }
        ]
    },
    "code": 0,
    "message": "OK",
    "request_id": "9c8b515158dd4475b631913d4f6994a1"
}
```
### 响应参数说明
| 参数名称     | 参数类型   | 描述 |
| ------------ | ------------ |---------------- |
| id | int | 分区配置ID | 
| bk_biz_id | int | 业务ID | 
| immute_domain | string | 集群域名 | 
| port | int | 实例端口 | 
| bk_cloud_id | int | 实例资源云区域 | 
| cluster_id | int | 集群ID | 
| dblike | string | 分区表所在库 | 
| tblike | string | 分区表 | 
| partition_columns | string | 分区字段 | 
| partition_column_type | string | 分区字段类型 | 
| reserved_partition | int | 分区保留时间 | 
| extra_partition | int | 预留分区数（默认15） | 
| partition_time_interval | int | 分区间隔 | 
| partition_type | int | 分区类型 | 
| expire_time | int | 分区过期时间 | 
| time_zone | string | 时区 | 
| phase | string | 是否禁用分区 | 
| creator | string | 分区配置创建者 | 
| updator | string | 分区配置更新者 | 
| create_time | string | 分区配置创建时间 | 
| update_time | string | 分区配置更新时间 | 
| execute_time | string | 分区执行时间 | 
| ticket_id | int | 分区单据ID | 
| status | string | 最近分区执行状态 | 
| ticket_status | string | 单据状态 | 
| check_info | string | 分区检查信息 |