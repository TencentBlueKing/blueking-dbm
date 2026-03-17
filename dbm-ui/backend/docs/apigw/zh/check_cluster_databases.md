### 描述

查询集群的库是否存在

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id    | int         | 是     | 业务id           |
| cluster_id   | int         | 是     | 集群id           |
| db_list      | array       | 是     | 数据库名称列表   |



### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/dbbase/check_cluster_databases/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "bk_biz_id": 3,
  "cluster_id":  1000072,
  "db_list": [
    "tes"
  ]
}'
```

### 响应示例
```python
{
  "data": {
    "tes": false
  },
  "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "2503b0c4736e40cc82dd3b77e451a049"
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| data         | dict       | 数据                           |
| tes          | bool       | 数据库是否存在                       |
| code         | int        | 响应码                         |
| result       | bool       | 结果                           |
| message      | string     | 消息                           |
| request_id   | string     | 请求id                         |