
### 功能描述

本接口用于spider以及mysql权限申请。该接口为异步接口，接口返回成功后，需要调用轮询接口，轮询授权状态。

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号

### 请求参数:

|参数名称|是否必须|类型|参数说明|
|---|---|---|---|
|bk_biz_id|N|int|业务ID|
|app|N|string|[GCS专属]GCS业务缩写，如qxzb|
|user|Y|string|授权账号|
|access_db|Y|string|准入DB|
|source_ips|Y|string|源IP列表，多个以逗号,分割|
|target_instance|Y|string|目标域名，这里仅支持单个域名|
|operator|N|string|提单操作者|
|type|N|string|[GCS专属]GCS授权类型|
|set_name|N|string|[GCS专属]Set名称，多个以逗号分隔|
|module_host_info|N|string|[GCS专属]模块主机信息|
|module_name_list|N|string|[GCS专属]模块列表|

注意：这里优先使用DBM平台，如果授权的目标域名不在DBM平台，才会使用GCS平台授权。关于GCS授权接口相关信息，可查看：[https://apigw.example.com/docs/component-api/ieod/GCS/mysql_privileges/doc](https://apigw.example.com/docs/component-api/ieod/GCS/mysql_privileges/doc "https://apigw.example.com/docs/component-api/ieod/GCS/mysql_privileges/doc")  
(关于网关的正式环境，可询问相关同学。涉及敏感信息这里暂时屏蔽)

#### 关于授权类型type：  
如果是DBM授权，则会根据域名对应的集群自动查询；如果是GCS平台，则需要确定好自己的type。  
GCS的type类型：  
-mysql:表示mysql权限申请，读取mysql的权限模版条目  
-spider:表示spider权限申请，读取spider的权限模版条目  
-mysql_ignoreCC：表示mysql权限申请，读取mysql gcs_ignore_cc模块的权限模版条目  
-spider_ignoreCC： 表示spider权限申请，读取spider gcs_ignore_cc模块的权限模版条目  
备注：  
mysql_ignoreCC与spider_ignoreCC读取的都是权限模版中“访问来源模块”写死“gcs_ignore_cc”的条目

#### 关于业务缩写app：  
如果是DBM授权，则无需传递，只需要bk_biz_id即可；如果是GCS平台，则必须传递此参数。  
如果并不确定是在哪个平台进行授权，可以优选考虑同时传递bk_biz_id和app。如果没有办法获取bk_biz_id，则也可以只传app，后台会根据app反查出bk_biz_id。

#### 关于 operator ：  
单据创建人（或者叫 提交者）

- 对于集群在gcs，operator 如果传递了值，则会以这个用户名权限申请单据的提交者，所以需要这个用户有gcs对应的app权限。如果不传，默认都有权限。需要平台调用方根据需求设置。
- 对于集群在 dbm，在网关鉴权使用的是 header中X-Bkapi-Authorization字典里的bk_username。 默认也以请求body里的operator字段作为单据提交者。如果不传，则使用header中X-Bkapi-Authorization::bk_username 为提交者。  
    如果想让提交者也走网关的鉴权，请在X-Bkapi-Authorization::bk_username的值设置为真实提交用户。

简单说，网关鉴权对象以header bk_username，提单人优先以 body operator为准，如果想要网关鉴权对象是提单人，则header bk_username就要赋值为提单人。

### 请求参数示例


```json
{
	"bk_biz_id": 1,
	"app":"abc",
	"user": "admin",
	"access_db": "test",
	"source_ips": "127.0.0.1,127.0.0.2",
	"target_instance": "gamedb.xxx.dba.db",
	"type": "mysql_ignoreCC"
}



```

### 响应示例:

```json
{
    "data": {
        "task_id": 888,
        "platform": "dbm"
    },
    "code": 0,
    "message": "OK",
    "request_id": "fa0a096e325f43cdcds845dbb646f05e5"
}
```

### 返回响应参数

|参数名称|是否必须|类型|参数说明|
|---|---|---|---|
|task_id|Y|int|任务ID|
|platform|Y|string|授权平台：gcs/dbm|

返回的 task_id, platform 后面可用于查询单据状态