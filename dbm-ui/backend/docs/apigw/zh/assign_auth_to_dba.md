### 描述

自动分配权限给DBA
### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|

### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id    | int         | 是     | 业务id           |
| group_name   | string      | 是     | 组名称           |
| members      | array       | 是     | 成员列表         |



### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/iam/assign_auth_to_dba/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "bk_biz_id": 0,
  "group_name": "string",
  "members": [
    "string"
  ]
}'
```

### 响应示例
```python
{
  "code": 0,
  "request_id": "string",
  "data": {
    "bk_biz_id": 0,
    "group_name": "",
    "members": [
      "string"
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
| bk_biz_id    | int        | 业务id                         |
| group_name   | string     | 分组名称                       |
| members      | list       | 成员列表                       |