### 描述

检查当前用户对该动作是否有权限(仅适用于鉴权业务下一个动作对应一种资源类型，如果是多种动作对应多种资源类型，请切换为check_allowed接口)

### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| action_ids        | array       | 是     | 操作ID列表     |
| resources        | array       | 是     | 资源列表     |
| resources.type        | string       | 是     | 资源类型     |
| resources.id        | string       | 是     | 资源ID     |


### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/iam/check_allowed/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -d '{
  "action_ids": [
    "string"
  ],
  "resources": [
    {
      "type": "string",
      "id": "string"
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
      "action_id": "mysql_apply",
      "is_allowed": true
    }
  ]
}
```

| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| code         | int        | 响应状态码                     |
| request_id   | string     | 请求ID                         |
| data         | list       | 权限数据列表                   |
| action_id    | string     | 操作ID                         |
| is_allowed   | boolean    | 是否允许操作                   |