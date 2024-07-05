### 功能描述

更新分区配置

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

### 请求参数示例
```json
{
    "cluster_id":133,
    "dblikes":["db_worldsvr_example"],
    "tblikes":["Player"],
    "partition_column":"ID",
    "partition_column_type":"int",
    "expire_time":10,
    "partition_time_interval":1
}
```
### 返回结果示例
```json
{
    "data": "更新分区配置信息创建成功！",
    "code": 0,
    "message": "OK",
    "request_id": "e7861d0e4f5c4dd0a82dc6f762a13e18"
}
```