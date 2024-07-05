### 描述

创建权限规则

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| account_id         | int       | 是     | 用户ID    |
| access_db         | string       | 是     | 访问DB，可填 % 代表全部     |
| account_type | string   | 是   | 账号类型(mysql \| tendbcluster \| sqlserver \| mongodb) |
| privilege         | object       | 是     | 权限规则     |
| privilege.ddl         | array       | 是     | ddl权限，可选项：create, alter, drop, index, execute, create view     |
| privilege.dml         | array       | 是     | dml权限，可选项：select,insert,update,delete   |
| privilege.glob         | array       | 是     | glob权限，可选项：file,trigger,event,create routine,alter routine,replication client,replication slave,reload,process,show databases     |


### 请求参数示例


```json
{
  "account_id": 123,
  "access_db": "%",
  "privilege": {"ddl":[],"dml":["select"],"glob":[]}
}
```


### 响应示例
```python
{
    "data": {},
    "code": 0,
    "message": "OK",
    "request_id": "510cd177fxxxxxaebb93a03f"
}
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
|              |            |                                |