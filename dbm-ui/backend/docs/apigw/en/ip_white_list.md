### Description

IP whitelist list

### Input Parameters
| Parameter Name | Parameter Type | Required | Description         |
| ---------- | -------- | ---- | ------------ |
| bk_biz_id  | int      | Yes  | Business ID      |
| ip         | string   | No   | IP address      |
| ids        | array    | No   | ID list      |
| limit      | int      | No   | Pagination limit quantity |
| offset     | int      | No   | Pagination offset   |


### Call Example
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

### Response Example
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

### Response Parameter Description
| Parameter Name | Parameter Type | Description |
| -------- | -------- | ---- |
| data | dict | Response data |
| data.count | int | Total number of data |
| data.results | list | Result list |
| data.permission | dict | Permission information |
| data.permission.ip_whitelist_manage | bool | Whether has IP whitelist management permission |
| data.permission.global_ip_whitelist_manage | bool | Whether has global IP whitelist management permission |
| code | int | Response status code |
| result | bool | Whether the request is successful |
| message | string | Response message |
| request_id | string | Request ID |