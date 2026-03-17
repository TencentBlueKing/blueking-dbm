### Description

Task details

### Input Parameters
| Parameter Name | Parameter Type | Required | Description |
| -------------- | --------------- | -------- | ----------- |
| root_id        | int             | Yes      | Task flow ID |

### Call Example
```python
curl -X 'GET' \
  'http://example.com/apis/taskflow/1/' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### Response Example
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

### Response Parameter Description
| Parameter Name | Parameter Type | Description |
| -------------- | --------------- | ----------- |
| code           | int             | Response status code |
| request_id     | string          | Request ID |
| data           | dict            | Ticket data |
| data.root_id   | string          | Root ID |
| data.ticket_type | string        | Ticket type |
| data.ticket_type_display | string | Display name of ticket type |
| data.flow_alias | string         | Flow alias |
| data.status    | string          | Ticket status |
| data.uid       | string          | User ID |
| data.created_by | string         | Creator |
| data.created_at | string         | Creation time |
| data.updated_at | string         | Update time |
| data.cost_time | string          | Time consumed |
| data.bk_biz_id | int             | Business ID |
| data.bk_biz_name | string        | Business name |