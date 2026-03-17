### Description

Automatically assign permissions to DBA  
### Headers  
| Parameter Name     | Parameter Type     | Required   | Description             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | Yes     | application/json     |
| X-Bkapi-Authorization | dict | Yes | Contains bk_app_code, bk_app_secret, bk_username |

### Input Parameters  
| Parameter Name     | Parameter Type     | Required   | Description             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id    | int         | Yes     | Business ID           |
| group_name   | string      | Yes     | Group name           |
| members      | array       | Yes     | Member list         |

### Call Example  
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

### Response Example  
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

### Response Parameter Description  
| Parameter Name     | Parameter Type   | Description                           |
| ------------ | ---------- | ------------------------------ |
| code         | int        | Response code                         |
| request_id   | string     | Request ID                         |
| data         | dict       | Data                           |
| bk_biz_id    | int        | Business ID                         |
| group_name   | string     | Group name                       |
| members      | list       | Member list                       |