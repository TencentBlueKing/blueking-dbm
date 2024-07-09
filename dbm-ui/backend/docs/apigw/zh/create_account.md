### 描述

创建账号

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| user         | string       | 是     | 用户名     |
| password         | string       | 是     | 密码（支持传明文或者国密加密密文）     |
| account_type | string   | 是   | 账号类型(mysql \| tendbcluster \| sqlserver \| mongodb) |


### 请求参数示例


```json
{
    "user": "username",
    "password": "password"
}
```


### 响应示例
```python
{
    "data": {"id": 123},
    "code": 0,
    "message": "OK",
    "request_id": "510cd177fxxxxxaebb93a03f"
}
```

### 响应参数说明
| 参数名称      | 参数类型     | 描述                           |
| ------------ | ---------- | ------------------------------ |
| id           |int         | 账号 ID                         |