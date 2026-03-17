### 描述

快速部署云区域组件

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号

### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id         | int       | 是     | 主机所在业务     |
| bk_cloud_id         | int       | 是     | 云区域id     |
|ips         | list       | 是     | IP列表     |


### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/tickets/fast_create_cloud_component/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "bk_biz_id": 3,
  "bk_cloud_id": 10000,
  "ips": [
    "0.0.0.0",
"0.0.0.0"
  ]
}'
```

### 响应示例
```python
{
 "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "152d20e1760645c5a5dae65a5c14212f",
  "data":{
    "bk_biz_id":3,
    "bk_cloud_id":10000,
    "ips":[
"0.0.0.0",
"0.0.0.0"
]
}
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| bk_biz_id             |int            | 主机所在业务                               |
| bk_cloud_id |int            |云区域id                               |
| ips             |list            | IP列表                               |