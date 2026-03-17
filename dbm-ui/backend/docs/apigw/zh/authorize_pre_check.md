### 描述

规则前置检查

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称           | 参数类型 | 必选 | 描述             |
| ------------------ | -------- | ---- | ---------------- |
| bk_biz_id          | int      | 是   | 业务id          |
| user               | string   | 是   | 用户名           |
| access_dbs         | array    | 是   | 访问数据库列表     |
| source_ips         | array    | 是   | 源IP列表         |
| target_instances   | array    | 是   | 目标实例列表       |
| cluster_type       | string   | 是   | 集群类型          |



### 调用示例
```python
curl -X 'POST' \
  'http://example.com/apis/mysql/bizs/3/permission/authorize/pre_check_rules/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "user": "admin",
  "access_dbs": [
    "user",
    "group"
  ],
  "source_ips": [
    {
      "bk_host_id": 1,
      "ip": "1.1.1.1"
    },
    {
      "bk_host_id": 2,
      "ip": "2.2.2.2"
    }
  ],
  "target_instances": [
    "gamedb.privtest55.blueking.db"
  ],
  "cluster_type": "tendbha"
}'
```

### 响应示例
```python
{
  "code": 0,
  "request_id": "string",
  "data": {
    "pre_check": true,
    "message": "ok",
    "authorize_uid": "c0e80efa2f5711ed99e7c2afcf9e926b",
    "authorize_data": {
      "user": "admin",
      "access_dbs": [
        "user",
        "group"
      ],
      "source_ips": [
        {
          "bk_host_id": 1,
          "ip": "1.1.1.1"
        },
        {
          "bk_host_id": 2,
          "ip": "2.2.2.2"
        }
      ],
      "target_instances": [
        "gamedb.privtest55.blueking.db"
      ],
      "cluster_type": "tendbha"
    }
  }
}
```

### 响应参数说明
| 参数名称 | 参数类型 | 描述 |
| -------- | -------- | ---- |
| code | int | 响应状态码 |
| request_id | string | 请求ID |
| data | dict | 响应数据 |
| data.pre_check | bool | 预检查是否通过 |
| data.message | string | 消息 |
| data.authorize_uid | string | 授权UID |
| data.authorize_data | dict | 授权数据 |
| data.authorize_data.user | string | 用户名 |
| data.authorize_data.access_dbs | list | 访问数据库列表 |
| data.authorize_data.source_ips | list | 源IP列表 |
| data.authorize_data.source_ips.bk_host_id | int | 主机ID |
| data.authorize_data.source_ips.ip | string | IP地址 |
| data.authorize_data.target_instances | list | 目标实例列表 |
| data.authorize_data.cluster_type | string | 集群类型 |