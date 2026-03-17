### 描述
通过库表匹配批量查询db

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|



### 输入参数
| 参数名称        | 参数类型     | 必选   | 描述             |
| --------------- | ------------ | ------ | ---------------- |
| bk_biz_id       | int         | 是     | 业务id           |
| cluster_ids     | array       | 是     | 集群id列表       |
| db_list         | array       | 是     | 数据库名称列表   |
| ignore_db_list  | array       | 是     | 忽略的数据库名称列表 |



### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/sqlserver/bizs/3/cluster/multi_get_sqlserver_dbs/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "cluster_ids": [
    1000072
  ],
  "db_list": [
    "test"
  ],
  "ignore_db_list": [
    
  ]
}'
```

### 响应示例
```python
{
  "code": 0,
  "request_id": "string",
  "data": {
    "1": [
      "db1",
      "db2",
      "db3"
    ]
  }
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| code         | int        | 响应码                         |
| request_id   | string     | 请求id                         |
| data         | dict       | 数据                           |