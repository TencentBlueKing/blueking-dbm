### 描述

构造实例列表
### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|

### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id    | int         | 是     | 业务id           |
| prod_cluster_id          | int       | 否     | 生产集群ID                     |
| prod_cluster             | string    | 否     | 生产集群                       |
| related_rollback_bill_id | int       | 否     | 关联回滚账单ID                 |
| temp_cluster_proxy       | string    | 否     | 临时集群代理                   |
| limit                     | int       | 否     | 每页数量限制                   |
| offset                    | int       | 否     | 偏移量                         |




### 调用示例
```python
curl -X 'GET' \
  'http://example.com/apis/redis/bizs/3/rollback/' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### 响应示例
```python
{
  "data": {
    "count": 0,
    "next": null,
    "previous": null,
    "results": []
  },
  "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "91f54cfd3f554c44aad6c270334ff49b"
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
| data         | dict       | 数据                           |
| count        | int        | 总数                           |
| next         | string     | 下一页链接                     |
| previous     | string     | 上一页链接                     |
| results      | list       | 结果列表                       |
| code         | int        | 响应码                         |
| result       | bool       | 结果                           |
| message      | string     | 消息                           |
| request_id   | string     | 请求id                         |