### 描述

创建DNS


### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|



### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| app          | string      | 是     | 应用名称         |
| bk_cloud_id  | int         | 是     | 云区域id         |
| domains      | array       | 是     | 域名列表         |



### 调用示例
```python
curl -X 'PUT' \
  'http://example.com/apis/legacy/dns/create_domain/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "app": "string",
  "bk_cloud_id": 0,
  "domains": [
    {
      "domain_name": "string",
      "instances": [
        "string"
      ],
      "manager": "string",
      "remark": "string",
      "domain_type": "string",
      "extends": "string"
    }
  ]
}'
```

### 响应示例
```python
{
  "code": 0,
  "request_id": "string",
  "data": {
    "app": "string",
    "bk_cloud_id": 0,
    "domains": [
      {
        "domain_name": "string",
        "instances": [
          "string"
        ],
        "manager": "string",
        "remark": "string",
        "domain_type": "string",
        "extends": "string"
      }
    ]
  }
}
```

### 响应参数说明
| 参数名称        | 参数类型   | 描述                           |
| --------------- | ---------- | ------------------------------ |
| code            | int        | 响应码                         |
| request_id      | string     | 请求id                         |
| data            | dict       | 数据                           |
| app             | string     | 应用                           |
| bk_cloud_id     | int        | 云区域id                       |
| domains         | list       | 域名列表                       |
| domain_name     | string     | 域名名称                       |
| instances       | list       | 实例列表                       |
| manager         | string     | 管理员                         |
| remark          | string     | 备注                           |
| domain_type     | string     | 域名类型                       |
| extends         | string     | 扩展信息                       |