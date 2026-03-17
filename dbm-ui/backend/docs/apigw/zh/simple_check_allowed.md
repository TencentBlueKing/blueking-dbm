### 描述

检查当前用户对该动作是否有权限(仅适用于鉴权业务下一个动作对应一种资源类型，如果是多种动作对应多种资源类型，请切换为check_allowed接口)

### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id        | string       | 是     | 业务ID     |
| action_id        | string       | 是     | 操作ID     |
| resource_id        | string       | 是     | 资源ID     |
| is_raise_exception        | boolean       | 是     | 是否抛出异常     |

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/iam/simple_check_allowed/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "bk_biz_id": "0",
  "action_id": "string",
  "resource_id": "string",
  "is_raise_exception": false
}'
```

### 响应示例
```python
{
  "code": 0,
  "request_id": "string",
  "data": {
    "bk_biz_id": "0",
    "action_id": "string",
    "resource_id": "string",
    "is_raise_exception": false
  }
}
```

| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| code         | int        | 响应状态码                     |
| request_id   | string     | 请求ID                         |
| data         | dict       | 权限数据                       |
| bk_biz_id    | string        | 业务ID                         |
| action_id    | string     | 操作ID                         |
| resource_id  | string     | 资源ID                         |
| is_raise_exception| boolean| 是否抛出异常                   |