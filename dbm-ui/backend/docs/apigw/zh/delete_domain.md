### 描述

删除DNS


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
curl -X 'DELETE' \
  'http://example.com/apis/legacy/dns/delete_domain/' \
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
  "request_id": "string"
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| code         | int        | 响应码                         |
| request_id   | string     | 请求id                         |