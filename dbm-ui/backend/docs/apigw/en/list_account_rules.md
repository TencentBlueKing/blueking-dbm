### Description

Query the account rule list

### Request Headers

```json
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```
* `bk_app_code` and `bk_app_secret` need to be applied for in the BlueKing Developer Center  
* `bk_username`: is the username of the caller; if it is a platform-level call, a virtual account needs to be applied for in advance  

| Parameter Name | Parameter Type | Required | Description                                                    |
| -------------- | -------------- | -------- | --------------------------------------------------------------- |
| limit          | int            | No       | Pagination limit                                                |
| offset         | int            | No       | Pagination start index                                          |
| rule_ids       | string         | No       | Rule ID list (separated by commas)                              |
| user           | string         | No       | Account name                                                    |
| access_db      | string         | No       | Accessed DB                                                     |
| privilege      | string         | No       | Rule list                                                       |
| account_type   | string         | Yes      | Account type (mysql, tendbcluster)                              |
| bk_biz_id      | int            | Yes      | Business ID                                                     |
| account_type   | string         | Yes      | Account type (mysql \| tendbcluster \| sqlserver \| mongodb)    |

### 

### Call Example
```python
from bkapi.bkdbm.shortcuts import get_client_by_request

client = get_client_by_request(request)
result = client.api.api_test({}, path_params={}, headers=None, verify=True)
```

### Response Example
```json
{
  "code": 0,
  "request_id": "string",
  "data": {
    "count": 1,
    "items": [
      {
        "account": {
          "bk_biz_id": 1,
          "user": "admin",
          "creator": "admin",
          "create_time": "2022-09-06 20:20:17",
          "account_id": 31,
          "id": 1
        },
        "rules": [
          {
            "account_id": 31,
            "bk_biz_id": 1,
            "creator": "",
            "create_time": "2022-09-06 20:22:17",
            "id": 24,
            "dbname": "datamain",
            "priv": "select,update,delete,create"
          }
        ]
      }
    ]
  }
}
```