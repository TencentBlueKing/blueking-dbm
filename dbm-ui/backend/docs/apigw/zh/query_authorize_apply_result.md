
### 功能描述

本接口用于spider以及mysql权限申请结果查询，用于轮询的接口

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号

### 请求参数:

|参数名称|是否必须|类型|参数说明|
|---|---|---|---|
|task_id|Y|int|任务ID|
|platform|Y|string|授权平台|

### 请求示例


```javascript
curl -XGET 'https://xxx.example.com/prod/plugin/mysql/authorize/query_authorize_apply_result/?task_id=1&platform=dbm' \
-H 'Content-Type: application/json' \
-H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### 响应示例:

```json
{
    "data":{
        "status":"SUCCEEDED",
        "msg":"jobId: 13690814 SUCC"
    },
    "code":0,
    "message":"OK",
    "request_id":"510cd177fxxxxxaebb93a03f"
}
```

code = 0, 表示请求成功，单据状态参考 status 列

### 返回响应

|参数名称|是否必须|类型|参数说明|
|---|---|---|---|
|status|Y|string|结果状态, <br>关于status，有如下类型：  <br>"PENDING", ("等待中")  <br>"RUNNING", ("执行中")  <br>"SUCCEEDED", ("成功")  <br>"FAILED", ("失败")  <br>"REVOKED", ("撤销") |
|msg|Y|string|结果信息|

其中PENDING和RUNNING可以认为还在继续，需要继续轮询。SUCCEEDED就表示授权成功，其他状态则表示失败。
