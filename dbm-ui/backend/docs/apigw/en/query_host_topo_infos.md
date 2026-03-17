### Description

Filter and query the topology information of hosts based on primary key

### Input Parameters
| Parameter Name       | Parameter Type | Required | Description             |
| -------------------- | -------------- | -------- | ----------------------- |
| bk_biz_id            | int            | Yes      | Business ID             |
| filter_conditions    | object         | Yes      | Filter conditions       |



### Call Example
```python
curl -X 'POST' \
  'http://example.com/apis/ipchooser/topo/query_host_topo_infos/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{
  "bk_biz_id": 200050000,
  "filter_conditions": {
    "bk_host_innerip": [
      "0:127.0.0.1",
      "0:127.0.0.2"
    ]
  }
}'
```

### Response Example
```python
{
  "total": 2,
  "hosts_topo_info": [
    {
      "bk_host_id": 248517489,
      "ip": "127.0.0.1",
      "topo": [
        "biz1/set1/module1/",
        "biz1/set3/module2/"
      ]
    },
    {
      "bk_host_id": 248517490,
      "ip": "127.0.0.2",
      "topo": [
        "biz1/set2/module2/",
        "biz3/set3/module2/"
      ]
    }
  ]
}
```

### Response Parameter Description
| Parameter Name | Parameter Type | Description |
| -------------- | -------------- | ----------- |
| total          | int            | Total count |
| hosts_topo_info | list           | List of host topology information |
| hosts_topo_info.bk_host_id | int | Host ID |
| hosts_topo_info.ip | string | IP address |
| hosts_topo_info.topo | list | List of topology paths |