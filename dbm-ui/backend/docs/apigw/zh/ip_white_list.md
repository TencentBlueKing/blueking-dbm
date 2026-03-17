### 描述

ip白名单列表

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称   | 参数类型 | 必选 | 描述         |
| ---------- | -------- | ---- | ------------ |
| bk_biz_id  | int      | 是   | 业务id      |
| ip         | string   | 否   | IP地址      |
| ids        | array    | 否   | ID列表      |
| limit      | int      | 否   | 分页限制数量 |
| offset     | int      | 否   | 分页偏移量   |



### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/conf/ip_whitelist/iplist/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "bk_biz_id": 3,
  "ip": "",
  "ids": [
    0
  ],
  "limit": 10,
  "offset": 0
}'
```

### 响应示例
```python
{
  "data": {
    "count": 0,
    "results": [],
    "permission": {
      "ip_whitelist_manage": true,
      "global_ip_whitelist_manage": true
    }
  },
  "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "3c1ea74401c340afb7779590d018be48"
}
```

### 响应参数说明
| 参数名称 | 参数类型 | 描述 |
| -------- | -------- | ---- |
| data | dict | 响应数据 |
| data.count | int | 数据总数 |
| data.results | list | 结果列表 |
| data.permission | dict | 权限信息 |
| data.permission.ip_whitelist_manage | bool | 是否有IP白名单管理权限 |
| data.permission.global_ip_whitelist_manage | bool | 是否有全局IP白名单管理权限 |
| code | int | 响应状态码 |
| result | bool | 请求是否成功 |
| message | string | 响应消息 |
| request_id | string | 请求ID |