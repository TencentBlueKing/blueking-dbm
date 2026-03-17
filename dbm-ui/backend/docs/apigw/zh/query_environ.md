### 描述

查询环境变量

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| limit        | int       | 否     | 每页数量限制                   |
| offset       | int       | 否     | 偏移量                         |



### 调用示例
```python
curl -X 'GET' \
  'http://example.com/apis/conf/system_settings/environ/' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### 响应示例
```python
{
  "data": {
    "APP_CODE": "bk_dbm",
    "APP_VERSION": "",
    "BK_DOMAIN": ".example.com",
    "BK_HELPER_URL": null,
    "BK_DBM_URL": "http://example.com",
    "DBA_APP_BK_BIZ_ID": 3,
    "DBA_APP_BK_BIZ_NAME": "DBA",
    "RESOURCE_INDEPENDENT_BIZ": 3,
    "RESOURCE_INDEPENDENT_BIZ_NAME": "DBA",
    "CC_MANAGE_TOPO": {
      "set_id": 34,
      "pending.module": 2688,
      "dirty_module_id": 821,
      "resource_module_id": 306,
      "resource.idle.module": 306
    },
    "AFFINITY": [
      {
        "label": "跨园区",
        "value": "CROS_SUBZONE"
      },
      {
        "label": "制定园区",
        "value": "SAME_SUBZONE_CROSS_SWTICH"
      },
      {
        "label": "不限园区",
        "value": "CROSS_RACK"
      },
      {
        "label": "无",
        "value": "NONE"
      }
    ],
    "ENABLE_EXTERNAL_PROXY": false,
    "DBA_ROBOT": {
      "es": "SCC_TENDATA_HELPER",
      "hdfs": "SCC_TENDATA_HELPER",
      "doris": "SCC_TENDATA_HELPER",
      "kafka": "SCC_TENDATA_HELPER",
      "pulsar": "SCC_TENDATA_HELPER"
    },
    "ENABLE_DBM_AI": false,
    "CC_IDLE_MODULE_ID": 7,
    "BK_COMPONENT_API_URL": "http://example.com",
    "BK_CMDB_URL": "http://cmdb.example.com",
    "BK_NODEMAN_URL": "http://apps.example.com/bk--nodeman",
    "BK_SCR_URL": "http://scr.example.com",
    "BKDATA_FRONTEND_REPORT_URL": "http://example.com/api/c/compapi/v2/bkbase/v4/report_data/569035/",
    "BK_AIDEV_URL": null,
    "BK_AIDEV_LOG_ANALYSIS_URL": null,
    "BKMONITOR_URL": "http://example.com/",
    "BK_HCM_URL": ""
  },
  "code": 0,
  "result": true,
  "message": "OK",
  "request_id": "843a659ede7d41e599352cfbb58d29fa"
}
```

### 响应参数说明
| 参数名称                          | 参数类型   | 描述                           |
| --------------------------------- | ---------- | ------------------------------ |
| data                              | dict       | 数据                           |
| APP_CODE                          | string     | 应用代码                       |
| APP_VERSION                       | string     | 应用版本                       |
| BK_DOMAIN                         | string     | 蓝鲸域名                       |
| BK_HELPER_URL                     | string     | 蓝鲸助手URL                    |
| BK_DBM_URL                        | string     | 蓝鲸DBM URL                    |
| DBA_APP_BK_BIZ_ID                 | int        | DBA应用业务id                  |
| DBA_APP_BK_BIZ_NAME               | string     | DBA应用业务名称                |
| RESOURCE_INDEPENDENT_BIZ          | int        | 资源独立业务id                 |
| RESOURCE_INDEPENDENT_BIZ_NAME     | string     | 资源独立业务名称               |
| CC_MANAGE_TOPO                    | dict       | CMDB管理拓扑                   |
| set_id                            | int        | 集群id                         |
| pending.module                    | int        | 待处理模块id                   |
| dirty_module_id                   | int        | 脏模块id                       |
| resource_module_id                | int        | 资源模块id                     |
| resource.idle.module              | int        | 资源空闲模块id                 |
| AFFINITY                          | list       | 亲和性列表                     |
| label                             | string     | 标签                           |
| value                             | string     | 值                             |
| ENABLE_EXTERNAL_PROXY             | bool       | 是否启用外部代理               |
| DBA_ROBOT                         | dict       | DBA机器人                      |
| es                                | string     | ES机器人                       |
| hdfs                              | string     | HDFS机器人                     |
| doris                             | string     | Doris机器人                    |
| kafka                             | string     | Kafka机器人                    |
| pulsar                            | string     | Pulsar机器人                   |
| ENABLE_DBM_AI                     | bool       | 是否启用DBM AI                 |
| CC_IDLE_MODULE_ID                 | int        | CMDB空闲模块id                 |
| BK_COMPONENT_API_URL              | string     | 蓝鲸组件API URL                |
| BK_CMDB_URL                       | string     | 蓝鲸CMDB URL                   |
| BK_NODEMAN_URL                    | string     | 蓝鲸节点管理URL                |
| BK_SCR_URL                        | string     | 蓝鲸SCR URL                    |
| BKDATA_FRONTEND_REPORT_URL        | string     | BKDATA前端上报URL              |
| BK_AIDEV_URL                      | string     | 蓝鲸AI开发URL                  |
| BK_AIDEV_LOG_ANALYSIS_URL         | string     | 蓝鲸AI开发日志分析URL          |
| BKMONITOR_URL                     | string     | 蓝鲸监控URL                    |
| BK_HCM_URL                        | string     | 蓝鲸HCM URL                    |
| code                              | int        | 响应码                         |
| result                            | bool       | 结果                           |
| message                           | string     | 消息                           |
| request_id                        | string     | 请求id                         |