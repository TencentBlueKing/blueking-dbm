### 描述

资源导入
### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|

### 输入参数
| 参数名称          | 参数类型     | 必选   | 描述             |
| ----------------- | ------------ | ------ | ---------------- |
| for_biz           | int         | 是     | 业务标识         |
| resource_type     | string      | 是     | 资源类型         |
| bk_biz_id         | int         | 是     | 业务id           |
| hosts             | array       | 是     | 主机列表         |
| labels            | array       | 是     | 标签列表         |
| return_resource   | boolean     | 是     | 是否返回资源     |
| os_type           | string      | 是     | 操作系统类型     |
| label_names       | array       | 是     | 标签名称列表     |



### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/dbresource/resource/import/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "for_biz": 0,
  "resource_type": "string",
  "bk_biz_id": 3,
  "hosts": [
    {
      "ip": "string",
      "host_id": 0,
      "bk_cloud_id": 0,
      "status": "string",
      "city_name": "string",
      "sub_zone": "string",
      "rack_id": "string",
      "bk_os_name": "string",
      "svr_device_class": "string",
      "bk_cloud_name": "string"
    }
  ],
  "labels": [
    "string"
  ],
  "return_resource": true,
  "os_type": "1",
  "label_names": [
    "string"
  ]
}'
```

### 响应示例
```python
{
  "code": 0,
  "request_id": "string",
  "data": ""
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| code         | int        | 响应码                         |
| request_id   | string     | 请求id                         |
| data         | string     | 数据                           |