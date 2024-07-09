### 描述

查询账号规则清单

### 请求头

```json
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```
* bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
* bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号


| 参数名称     | 参数类型 | 必选 | 描述                                                    |
| ------------ | -------- | ---- | ------------------------------------------------------- |
| limit        | int      | 否   | 分页限制                                                |
| offset       | int      | 否   | 分页起始                                                |
| rule_ids     | string   | 否   | 规则ID列表(通过,分割)                                   |
| user         | string   | 否   | 账号名称                                                |
| access_db    | string   | 否   | 访问DB                                                  |
| privilege    | string   | 否   | 规则列表                                                |
| account_type | string   | 是   | 账号类型(mysql, tendbcluster)                           |
| bk_biz_id    | int      | 是   | 业务ID                                                  |
| account_type | string   | 是   | 账号类型(mysql \| tendbcluster \| sqlserver \| mongodb) |

### 

### 调用示例
```python
from bkapi.bkdbm.shortcuts import get_client_by_request

client = get_client_by_request(request)
result = client.api.api_test({}, path_params={}, headers=None, verify=True)
```

### 响应示例
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