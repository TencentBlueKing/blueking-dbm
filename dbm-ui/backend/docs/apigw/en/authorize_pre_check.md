### Description

Pre-check for rules

### Input Parameters
| Parameter Name           | Parameter Type | Required | Description             |
| ------------------------ | -------------- | -------- | ----------------------- |
| bk_biz_id                | int            | Yes      | Business ID             |
| user                     | string         | Yes      | Username                |
| access_dbs               | array          | Yes      | List of databases to access |
| source_ips               | array          | Yes      | Source IP list          |
| target_instances         | array          | Yes      | Target instance list    |
| cluster_type             | string         | Yes      | Cluster type            |



### Call Example
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

### Response Example
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

### Response Parameter Description
| Parameter Name | Parameter Type | Description |
| -------------- | -------------- | ----------- |
| code           | int            | Response status code |
| request_id     | string         | Request ID |
| data           | dict           | Response data |
| data.pre_check | bool           | Whether pre-check passed |
| data.message   | string         | Message |
| data.authorize_uid | string      | Authorization UID |
| data.authorize_data | dict       | Authorization data |
| data.authorize_data.user | string | Username |
| data.authorize_data.access_dbs | list | List of databases to access |
| data.authorize_data.source_ips | list | Source IP list |
| data.authorize_data.source_ips.bk_host_id | int | Host ID |
| data.authorize_data.source_ips.ip | string | IP address |
| data.authorize_data.target_instances | list | Target instance list |
| data.authorize_data.cluster_type | string | Cluster type |