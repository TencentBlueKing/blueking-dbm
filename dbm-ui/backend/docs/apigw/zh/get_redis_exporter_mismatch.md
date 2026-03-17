### 描述

获取redis集群的exporter数与分片数不一致的报表


### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |



### 调用示例
```python
curl -X 'POST' \
  'http://example.com/db_report/exporter/get_redis_exporter_mismatch/' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}' \
  -d '{}'
```

### 响应示例
```python
{
  "data": [
    {
      "domain": null,
      "shard": 6,
      "exporter_up": 0
    },
    {
      "domain": "cache.redis6-test.kio.db",
      "shard": 3,
      "exporter_up": 0
    },
    {
      "domain": "ins.w2.only-dba-test.db",
      "shard": 1,
      "exporter_up": 0
    },
    {
      "domain": "ins.abc.only-dba-test.db",
      "shard": 1,
      "exporter_up": 0
    },
    {
      "domain": "ins.test002.kio.db",
      "shard": 1,
      "exporter_up": 0
    },
    {
      "domain": "ssd.ddgzssd.only-dba-test.db",
      "shard": 6,
      "exporter_up": 0
    },
    {
      "domain": "ins.b1-test.kio.db",
      "shard": 1,
      "exporter_up": 0
    },
    {
      "domain": "ins.b2-test.kio.db",
      "shard": 1,
      "exporter_up": 0
    },
    {
      "domain": "ins.b3-test.kio.db",
      "shard": 1,
      "exporter_up": 0
    },
    {
      "domain": "ins.a1-test.kio.db",
      "shard": 1,
      "exporter_up": 0
    },
    {
      "domain": "ins.a2-test.kio.db",
      "shard": 1,
      "exporter_up": 0
    },
    {
      "domain": "ins.a3-test.kio.db",
      "shard": 1,
      "exporter_up": 0
    }
  ],
  "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "c356d6f8464347af845c815f30756180"
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| data         | list       | 响应数据列表                   |
| domain       | string     | 域名                           |
| shard        | int        | 分片数                         |
| exporter_up  | int        | 导出器状态                     |
| code         | int        | 响应状态码                     |
| result       | bool       | 响应结果                       |
| message      | string     | 响应消息                       |
| request_id   | string     | 请求ID                         |