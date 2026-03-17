### 描述

查询账号规则清单

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称      | 参数类型     | 必选   | 描述             |
| ------------- | ------------ | ------ | ---------------- |
| bk_biz_id     | int         | 是     | 业务id           |
| account_type  | string      | 是     | 账户类型         |
| limit        | int       | 否     | 每页数量限制                   |
| offset       | int       | 否     | 偏移量                         |
| rule_ids     | string    | 否     | 规则ID列表(,分割)                     |
| user         | string    | 否     | 用户                           |
| access_db    | string    | 否     | 访问数据库                     |
| prvilege     | string    | 否     | 权限                           |




### 调用示例
```python
curl -X 'GET' \
  'http://example.com/apis/sqlserver/bizs/3/permission/account/list_account_rules/?account_type=mysql' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### 响应示例
```python
{
  "data": {
    "count": 136,
    "results": [
      {
        "account": {
          "bk_biz_id": 3,
          "user": "admin",
          "creator": "admin",
          "create_time": "2023-08-07T21:34:30Z",
          "account_id": 1
        },
        "rules": [
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "admin",
            "create_time": "2024-05-24T09:18:44Z",
            "rule_id": 309,
            "access_db": "a2",
            "privilege": "select,insert,update,delete,show view,create,alter,drop,index,create view,execute,trigger,event,create routine,alter routine,references,create temporary tables,file,reload,show databases,process,replication slave,replication client",
            "priv_ticket": {}
          },
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "",
            "create_time": "2024-06-15T03:49:04Z",
            "rule_id": 320,
            "access_db": "db12",
            "privilege": "insert,update,delete,create,alter,create view,alter routine,file,reload,replication slave",
            "priv_ticket": {}
          },
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "",
            "create_time": "2024-06-15T03:49:04Z",
            "rule_id": 321,
            "access_db": "db2",
            "privilege": "select,insert,delete,show view,create,index",
            "priv_ticket": {}
          },
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "",
            "create_time": "2024-06-15T03:49:04Z",
            "rule_id": 322,
            "access_db": "db3",
            "privilege": "select,show view,alter,trigger",
            "priv_ticket": {}
          },
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "",
            "create_time": "2024-08-15T04:04:55Z",
            "rule_id": 498,
            "access_db": "a12",
            "privilege": "select,insert,update,delete,show view,create,index,file",
            "priv_ticket": {}
          },
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "",
            "create_time": "2024-08-15T04:10:23Z",
            "rule_id": 499,
            "access_db": "a33",
            "privilege": "select,insert,delete,create,index,references",
            "priv_ticket": {}
          },
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "",
            "create_time": "2024-09-02T07:31:17Z",
            "rule_id": 507,
            "access_db": "okok",
            "privilege": "select,index,create view,file",
            "priv_ticket": {}
          },
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "",
            "create_time": "2024-09-02T07:33:16Z",
            "rule_id": 508,
            "access_db": "okokok",
            "privilege": "select",
            "priv_ticket": {}
          },
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "",
            "create_time": "2024-09-02T07:35:38Z",
            "rule_id": 509,
            "access_db": "nono22",
            "privilege": "select,insert,show view,alter",
            "priv_ticket": {}
          },
          {
            "account_id": 1,
            "bk_biz_id": 3,
            "creator": "",
            "create_time": "2024-09-02T07:36:31Z",
            "rule_id": 510,
            "access_db": "nnnn",
            "privilege": "select",
            "priv_ticket": {}
          }
        ],
        "permission": {
          "mysql_account_delete": true,
          "mysql_add_account_rule": true
        }
      },
      {
        "account": {
          "bk_biz_id": 3,
          "user": "ddd",
          "creator": "admin",
          "create_time": "2025-07-11T07:56:36Z",
          "account_id": 756
        },
        "rules": [],
        "permission": {
          "mysql_account_delete": true,
          "mysql_add_account_rule": true
        }
      },
      {
        "account": {
          "bk_biz_id": 3,
          "user": "gcs_db",
          "creator": "qq_873551943@po",
          "create_time": "2024-11-29T09:10:01Z",
          "account_id": 735
        },
        "rules": [],
        "permission": {
          "mysql_account_delete": true,
          "mysql_add_account_rule": true
        }
      },
      {
        "account": {
          "bk_biz_id": 3,
          "user": "xxxx",
          "creator": "admin",
          "create_time": "2023-09-13T17:42:20Z",
          "account_id": 10
        },
        "rules": [],
        "permission": {
          "mysql_account_delete": true,
          "mysql_add_account_rule": true
        }
      },
      {
        "account": {
          "bk_biz_id": 3,
          "user": "mssql_exporter",
          "creator": "admin",
          "create_time": "2024-09-12T07:49:10Z",
          "account_id": 706
        },
        "rules": [],
        "permission": {
          "mysql_account_delete": true,
          "mysql_add_account_rule": true
        }
      },
      {
        "account": {
          "bk_biz_id": 3,
          "user": "qqq",
          "creator": "admin",
          "create_time": "2025-07-11T15:34:13Z",
          "account_id": 760
        },
        "rules": [],
        "permission": {
          "mysql_account_delete": true,
          "mysql_add_account_rule": true
        }
      },
      {
        "account": {
          "bk_biz_id": 3,
          "user": "test_username",
          "creator": "",
          "create_time": "2024-06-05T09:49:53Z",
          "account_id": 285
        },
        "rules": [],
        "permission": {
          "mysql_account_delete": true,
          "mysql_add_account_rule": true
        }
      },
      {
        "account": {
          "bk_biz_id": 3,
          "user": "xxx",
          "creator": "admin",
          "create_time": "2025-07-11T07:57:04Z",
          "account_id": 757
        },
        "rules": [],
        "permission": {
          "mysql_account_delete": true,
          "mysql_add_account_rule": true
        }
      }
    ]
  },
  "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "3eb98696528f4dd68035a18a3bd6f7ea"
}
```

### 响应参数说明
| 参数名称                  | 参数类型   | 描述                           |
| ------------------------- | ---------- | ------------------------------ |
| data                      | dict       | 数据                           |
| count                     | int        | 总数                           |
| results                   | list       | 结果列表                       |
| account                   | dict       | 账户信息                       |
| bk_biz_id                 | int        | 业务id                         |
| user                      | string     | 用户名                         |
| creator                   | string     | 创建人                         |
| create_time               | string     | 创建时间                       |
| account_id                | int        | 账户id                         |
| rules                     | list       | 规则列表                       |
| account_id                | int        | 账户id                         |
| bk_biz_id                 | int        | 业务id                         |
| creator                   | string     | 创建人                         |
| create_time               | string     | 创建时间                       |
| rule_id                   | int        | 规则id                         |
| access_db                 | string     | 访问数据库                     |
| privilege                 | string     | 权限                           |
| priv_ticket               | dict       | 权限单据                       |
| permission                | dict       | 权限信息                       |
| mysql_account_delete      | bool       | MySQL账户删除权限              |
| mysql_add_account_rule    | bool       | MySQL添加账户规则权限          |
| code                      | int        | 响应码                         |
| result                    | bool       | 结果                           |
| message                   | string     | 消息                           |
| request_id                | string     | 请求id                         |