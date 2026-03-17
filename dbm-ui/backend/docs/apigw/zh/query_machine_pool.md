### 描述

获取集群访问入口信息

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| ips         | string       | 否    | ip过滤列表，逗号分隔    |
| bk_host_ids         | string       | 否    | 主机ID过滤，逗号分隔    |
| limit         | int       | 是     | 分页限制    |
| offset | int   | 是   | 分页起始 |

### 请求参数示例


```shell
curl -XGET $URL?ips=1.1.1.1,2.2.2.2&limit=10&offset=0
```


### 响应示例
```python
{
    "count": 61202,
    "next": "http://example.com/apis/db_dirty/query_machine_pool/?limit=10&offset=10",
    "previous": null,
    "results": [
        {
            // 主机属性信息
            "bk_host_id": 8592386,
            "creator": "admin",
            "create_at": "2025-04-01T16:09:01+08:00",
            "updater": "xxx",
            "update_at": "2025-04-08T15:20:50+08:00",
            "bk_cloud_id": 0,
            "ip": "1.1.1.1",
            "city": "广州",
            "sub_zone": "广州-云谷",
            "rack_id": "686146",
            "device_class": "S5.MEDIUM4",
            "os_name": "Tencent tlinux release 2.6 (tkernel4)",
            "bk_cpu": 2,
            "bk_mem": 3661,
            "bk_disk": 147,
            "agent_status": 1,
            // 所处主机池
            "pool": "",
            // 关联单据
            "ticket": 1000203,
            // 主机最近事件
            "latest_event": {
                "id": 2086,
                "creator": "xxx",
                "updater": "xxx",
                "bk_biz_id": 5016766,
                "ip": "1.1.1.1",
                "bk_host_id": 8592386,
                "event": "apply_resource",
                "to": null,
                "ticket": 1000203,
                "remark": ""
            }
        }
    ]
}
```