### 描述

根据库表正则查询集群库信息

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id    | int         | 是     | 业务id           |
| infos        | array       | 是     | 集群信息列表     |



### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/mysql/bizs/3/remote_service/show_databases_with_patterns/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "infos": [
    {
      "cluster_id": 0,
      "dbs": [
        "string"
      ],
      "ignore_dbs": [
        "string"
      ]
    }
  ]
}'
```

### 响应示例
```python
{
  "code": 0,
  "request_id": "string",
  "data": [
    {
      "cluster_id": 1,
      "databases": [
        "db1",
        "db2"
      ]
    },
    {
      "cluster_id": 2,
      "databases": [
        "db2",
        "db3"
      ]
    }
  ]
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| code         | int        | 响应码                         |
| request_id   | string     | 请求id                         |
| data         | list       | 数据列表                       |
| cluster_id   | int        | 集群id                         |
| databases    | list       | 数据库列表                     |