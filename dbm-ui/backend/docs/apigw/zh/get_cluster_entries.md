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
| bk_biz_id         | int       | 是     | 业务ID    |
| cluster_id         | int       | 是     | 集群ID     |
| entry_type | string   | 否   | 访问类型(polaris \| dns \| clb \| clbdns) |

### 请求参数示例


```shell
curl -XGET $URL?bk_biz_id=5005578&cluster_id=100&entry_type=polaris
```


### 响应示例
```python
{
  // 访问入口类型
  "cluster_entry_type": "polaris",
  // 访问入口角色（主域名/从域名）
  "role": "master_entry",
  // 访问域名
  "entry": "polaris.xxxxxxx.db",
  // 详细信息
  "target_details": [
    {
      "id": 145,
      "creator": "admin",
      "updater": "",
      "entry": 11630,
      "polaris_name": "polaris.xxxxxx.db",
      "polaris_l5": "xxxx:xxxx",
      "polaris_token": "xxxxxx",
      "alias_token": "",
      "url": "https://.....",
      "port": 50000
    }
  ]
}
```