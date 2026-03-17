### 描述

任务详情

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称 | 参数类型 | 必选 | 描述     |
| -------- | -------- | ---- | -------- |
| root_id  | int      | 是   | 任务流程id |



### 调用示例
```python
curl -X 'GET' \
  'http://example.com/apis/taskflow/1/' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### 响应示例
```python
{
  "code": 0,
  "request_id": "string",
  "data": {
    "root_id": "string",
    "ticket_type": "MYSQL_SINGLE_APPLY",
    "ticket_type_display": "string",
    "flow_alias": "string",
    "status": "CREATED",
    "uid": "string",
    "created_by": "string",
    "created_at": "2026-02-02T09:53:53.907Z",
    "updated_at": "2026-02-02T09:53:53.907Z",
    "cost_time": "string",
    "bk_biz_id": 2147483647,
    "bk_biz_name": "string"
  }
}
```

### 响应参数说明
| 参数名称 | 参数类型 | 描述 |
| -------- | -------- | ---- |
| code | int | 响应状态码 |
| request_id | string | 请求ID |
| data | dict | 单据数据 |
| data.root_id | string | 根ID |
| data.ticket_type | string | 单据类型 |
| data.ticket_type_display | string | 单据类型显示名称 |
| data.flow_alias | string | 流程别名 |
| data.status | string | 单据状态 |
| data.uid | string | 用户ID |
| data.created_by | string | 创建人 |
| data.created_at | string | 创建时间 |
| data.updated_at | string | 更新时间 |
| data.cost_time | string | 耗时 |
| data.bk_biz_id | int | 业务ID |
| data.bk_biz_name | string | 业务名称 |