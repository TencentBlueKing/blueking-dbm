### 描述

业务列表

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称 | 参数类型 | 必选 | 描述     |
| -------- | -------- | ---- | -------- |
| limit        | int       | 否     | 每页数量限制                   |
| offset       | int       | 否     | 偏移量                         |
| action       | string    | 否     | 查询的权限动作                   |




### 调用示例
```python
curl -X 'GET' \
  'http://example.com/apis/cmdb/list_bizs/' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### 响应示例
```python
{
  "data": [
    {
      "bk_biz_id": 2,
      "name": "蓝鲸",
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
      "name": "xxxx",
      "english_name": "xxxx",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 5,
      "name": "xxxx",
      "english_name": "xxxx",
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
      "name": "reggie测试业务",
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
      "name": "xxxx专用测试",
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
      "name": "joker测试",
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
      "name": "资源池弹性池",
      "english_name": "dba_resource",
      "permission": {
        "db_manage": true
      }
    },
    {
      "bk_biz_id": 27,
      "name": "验收专用业务",
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

### 响应参数说明
| 参数名称 | 参数类型 | 描述 |
| -------- | -------- | ---- |
| data | list | 业务列表 |
| data.bk_biz_id | int | 业务ID |
| data.name | string | 业务名称 |
| data.english_name | string | 业务英文名称 |
| data.permission | dict | 权限信息 |
| data.permission.db_manage | bool | 是否有数据库管理权限 |
| code | int | 响应状态码 |
| result | bool | 请求是否成功 |
| message | string | 响应消息 |
| request_id | string | 请求ID |