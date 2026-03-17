### Description

Create DNS


### Headers 
| Parameter Name     | Parameter Type     | Required   | Description             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | Yes     | application/json     |
| X-Bkapi-Authorization | dict | Yes | Contains bk_app_code, bk_app_secret, bk_username |


### Input Parameters
| Parameter Name     | Parameter Type     | Required   | Description             |
| ------------ | ------------ | ------ | ---------------- |
| app          | string      | Yes     | Application name         |
| bk_cloud_id  | int         | Yes     | Cloud area ID         |
| domains      | array       | Yes     | Domain list         |


### Call Example
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

### Response Example
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

### Response Parameter Description
| Parameter Name        | Parameter Type   | Description                           |
| --------------- | ---------- | ------------------------------ |
| code            | int        | Response code                         |
| request_id      | string     | Request ID                         |
| data            | dict       | Data                           |
| app             | string     | Application                           |
| bk_cloud_id     | int        | Cloud area ID                       |
| domains         | list       | Domain list                       |
| domain_name     | string     | Domain name                       |
| instances       | list       | Instance list                       |
| manager         | string     | Manager                         |
| remark          | string     | Remark                           |
| domain_type     | string     | Domain type                       |
| extends         | string     | Extended information                       |