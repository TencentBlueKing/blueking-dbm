### Description

Delete DNS


### Headers 
| Parameter Name     | Parameter Type     | Required   | Description             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | Yes     | application/json     |
|X-Bkapi-Authorization | dict | Yes | Contains bk_app_code, bk_app_secret, bk_username|



### Input Parameters
| Parameter Name     | Parameter Type     | Required   | Description             |
| ------------ | ------------ | ------ | ---------------- |
| app          | string      | Yes     | Application name         |
| bk_cloud_id  | int         | Yes     | Cloud area ID         |
| domains      | array       | Yes     | Domain list         |



### Call Example
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

### Response Example
```python
{
  "code": 0,
  "request_id": "string"
}
```

### Response Parameter Description
| Parameter Name     | Parameter Type   | Description                           |
| ------------ | ---------- | ------------------------------ |
| code         | int        | Response code                         |
| request_id   | string     | Request ID                         |