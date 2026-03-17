### 功能描述

查询用户是否具有机器的BF权限。

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号

### 返回结果示例

```json
{
    "data": [1, 2, 3]
}
```

### 返回结果参数说明

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| data | list | 是 | 特殊业务白名单 |