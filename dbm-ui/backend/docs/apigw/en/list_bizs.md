### Description

Business List

### Input Parameters
| Parameter Name | Parameter Type | Required | Description |
| -------------- | --------------- | -------- | ----------- |
| None           | -               | -        | No request parameters |



### Call Example
```python
curl -X 'GET' \
  'http://example.com/apis/cmdb/list_bizs/' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### Response Example
```python
{
  "data": [
    {
      "bk_biz_id": 2,
      "name": "BlueKing",
      "english_name": "fff",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 3,
      "name": "DBA",
      "english_name": "dba",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 4,
      "name": "xxx",
      "english_name": "xxx",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 5,
      "name": "xxxxxx",
      "english_name": "xxx",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 6,
      "name": "testbiz",
      "english_name": "testbiz",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 7,
      "name": "DBA_TEST",
      "english_name": "dba-test",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 8,
      "name": "DBA_DEV",
      "english_name": "dba-dev",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 9,
      "name": "biz1010",
      "english_name": "",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 10,
      "name": "zbin",
      "english_name": "zbin",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 11,
      "name": "lukexw",
      "english_name": "lukexw",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 12,
      "name": "ES-paasdb",
      "english_name": "tendata",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 13,
      "name": "Vito_test",
      "english_name": "vitocc",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 14,
      "name": "hayley",
      "english_name": "",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 15,
      "name": "dbtest",
      "english_name": "",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 16,
      "name": "EDTEST",
      "english_name": "edtest",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 17,
      "name": "bellketest",
      "english_name": "belktest",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 18,
      "name": "reggie test business",
      "english_name": "",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 19,
      "name": "yytest",
      "english_name": "yytest",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 20,
      "name": "xxxx",
      "english_name": "make",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 21,
      "name": "obtest",
      "english_name": "obtest",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 22,
      "name": "jam",
      "english_name": "jam",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 23,
      "name": "cyctest",
      "english_name": "cyctest",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 24,
      "name": "Joker test",
      "english_name": "jtest",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 25,
      "name": "dannytest",
      "english_name": "dannytest",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 26,
      "name": "Resource pool elastic pool",
      "english_name": "dba_resource",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 27,
      "name": "Acceptance dedicated business",
      "english_name": "only-dba-test",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 28,
      "name": "kevn",
      "english_name": "kevntest",
      "permission": {
        "db_manage": true
      }
    }
  ],
  "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "57f5aa561238427c97f011d043e24f40"
}
```

### Response Parameter Description
| Parameter Name | Parameter Type | Description |
| -------------- | --------------- | ----------- |
| data | list | Business list |
| data.bk_biz_id | int | Business ID |
| data.name | string | Business name |
| data.english_name | string | Business English name |
| data.permission | dict | Permission information |
| data.permission.db_manage | bool | Whether has database management permission |
| code | int | Response status code |
| result | bool | Whether the request is successful |
| message | string | Response message |
| request_id | string | Request ID |