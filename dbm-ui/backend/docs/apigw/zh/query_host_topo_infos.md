### 描述

根据主键过滤查询主机的拓扑信息

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称           | 参数类型 | 必选 | 描述             |
| ------------------ | -------- | ---- | ---------------- |
| bk_biz_id          | int      | 是   | 业务id          |
| filter_conditions  | object   | 是   | 过滤条件         |



### 调用示例
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

### 响应示例
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

### 响应参数说明
| 参数名称 | 参数类型 | 描述 |
| -------- | -------- | ---- |
| total | int | 总数 |
| hosts_topo_info | list | 主机拓扑信息列表 |
| hosts_topo_info.bk_host_id | int | 主机ID |
| hosts_topo_info.ip | string | IP地址 |
| hosts_topo_info.topo | list | 拓扑路径列表 |