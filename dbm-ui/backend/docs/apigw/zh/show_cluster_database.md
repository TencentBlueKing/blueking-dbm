### 描述

查询数据库列表

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id    | int         | 是     | 业务id           |
| cluster_ids  | array       | 是     | 集群id列表       |



### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/mysql/bizs/3/remote_service/show_cluster_databases/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "cluster_ids": [
    1000072
   
  ]
}'
```

### 响应示例
```python
{
  "data": [
    {
      "cluster_id": 1000072,
      "databases": [
        "teng_test"
      ],
      "system_databases": [
        "mysql",
        "test",
        "db_infobase",
        "information_schema",
        "performance_schema",
        "sys",
        "infodba_schema"
      ]
    }
  ],
  "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "c177868a369b428cad4a823c223d431a"
}
```

### 响应参数说明
| 参数名称          | 参数类型   | 描述                           |
| ----------------- | ---------- | ------------------------------ |
| data              | list       | 数据列表                       |
| cluster_id        | int        | 集群id                         |
| databases         | list       | 数据库列表                     |
| system_databases  | list       | 系统数据库列表                 |
| code              | int        | 响应码                         |
| result            | bool       | 结果                           |
| message           | string     | 消息                           |
| request_id        | string     | 请求id                         |