### Description

Save alarm subscription


### Request Headers

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code and bk_app_secret need to be applied for in the BlueKing Developer Center  
- bk_username: is the calling username; if it is a platform-level call, a virtual account needs to be applied for in advance  


### Input Parameters
| Parameter Name | Parameter Type | Required | Description             |
| -------------- | -------------- | -------- | ----------------------- |
| clusters       | array          | Yes      | Cluster information list |
| alert_level    | array          | Yes      | Alarm level list        |
| notice_ways    | array          | Yes      | Notification method list |


**clusters Parameter Description:**  
| Parameter Name   | Parameter Type | Required | Description   |
| ---------------- | -------------- | -------- | ------------- |
| cluster_domain   | string         | Yes      | Cluster domain |
| cluster_type     | string         | Yes      | Cluster type   |



### Call Example
```python
curl -X 'POST' \
  'http://example.com/apis/monitor/subscribe/save_subscribe/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-Bkapi-Authorization: {"access_token": "your_token"}'  \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -d '{
  "clusters": [
    {
      "cluster_domain": "string",
      "cluster_type": "tendbsingle"
    }
  ],
  "alert_level": [
    0
  ],
  "notice_ways": [
    "sms"
  ]
}'
```

### Response Example
```python
{
  "code": 0,
  "request_id": "string",
  "data": {
    "clusters": [
      {
        "cluster_domain": "string",
        "cluster_type": "tendbsingle"
      }
    ],
    "alert_level": [
      0
    ],
    "notice_ways": [
      "sms"
    ]
  }
}
```

### Response Parameter Description
| Parameter Name | Parameter Type | Description          |
| -------------- | -------------- | -------------------- |
| code           | int            | Return status code   |
| request_id     | string         | Request ID           |
| data           | dict           | Data object          |
| clusters       | list           | Cluster list         |
| cluster_domain | string         | Cluster domain       |
| cluster_type   | string         | Cluster type         |
| alert_level    | list           | Alarm level list     |
| notice_ways    | list           | Notification method list |