### 描述

保存告警订阅


### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号



### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| clusters     | array       | 是     | 集群信息列表     |
| alert_level  | array       | 是     | 告警级别列表     |
| notice_ways  | array       | 是     | 通知方式列表     |

**clusters 参数说明：**
| 参数名称        | 参数类型   | 必选   | 描述             |
| --------------- | ---------- | ------ | ---------------- |
| cluster_domain  | string     | 是     | 集群域名         |
| cluster_type    | string     | 是     | 集群类型         |



### 调用示例
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

### 响应示例
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

### 响应参数说明
| 参数名称 | 参数类型 | 描述 |
| --- | --- | --- |
| code | int | 返回状态码 |
| request_id | string | 请求ID |
| data | dict | 数据对象 |
| clusters | list | 集群列表 |
| cluster_domain | string | 集群域名 |
| cluster_type | string | 集群类型 |
| alert_level | list | 告警级别列表 |
| notice_ways | list | 通知方式列表 |