### Description

Query environment variables

### Headers 
| Parameter Name     | Parameter Type     | Required   | Description             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | Yes     | application/json     |
| X-Bkapi-Authorization | dict | Yes | Contains bk_app_code, bk_app_secret, bk_username |


### Input Parameters
| Parameter Name     | Parameter Type     | Required   | Description             |
| ------------ | ------------ | ------ | ---------------- |
| limit        | int       | No     | Limit of items per page                   |
| offset       | int       | No     | Offset                         |


### Call Example
```python
curl -X 'GET' \
  'http://example.com/apis/conf/system_settings/environ/' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'
```

### Response Example
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
        "label": "Cross-zone",
        "value": "CROS_SUBZONE"
      },
      {
        "label": "Specified zone",
        "value": "SAME_SUBZONE_CROSS_SWTICH"
      },
      {
        "label": "No zone restriction",
        "value": "CROSS_RACK"
      },
      {
        "label": "None",
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

### Response Parameter Description
| Parameter Name                          | Parameter Type   | Description                           |
| --------------------------------- | ---------- | ------------------------------ |
| data                              | dict       | Data                           |
| APP_CODE                          | string     | Application code                       |
| APP_VERSION                       | string     | Application version                       |
| BK_DOMAIN                         | string     | BlueKing domain                       |
| BK_HELPER_URL                     | string     | BlueKing helper URL                    |
| BK_DBM_URL                        | string     | BlueKing DBM URL                    |
| DBA_APP_BK_BIZ_ID                 | int        | DBA application business ID                  |
| DBA_APP_BK_BIZ_NAME               | string     | DBA application business name                |
| RESOURCE_INDEPENDENT_BIZ          | int        | Resource independent business ID                 |
| RESOURCE_INDEPENDENT_BIZ_NAME     | string     | Resource independent business name               |
| CC_MANAGE_TOPO                    | dict       | CMDB management topology                   |
| set_id                            | int        | Cluster ID                         |
| pending.module                    | int        | Pending module ID                   |
| dirty_module_id                   | int        | Dirty module ID                       |
| resource_module_id                | int        | Resource module ID                     |
| resource.idle.module              | int        | Resource idle module ID                 |
| AFFINITY                          | list       | Affinity list                     |
| label                             | string     | Label                           |
| value                             | string     | Value                             |
| ENABLE_EXTERNAL_PROXY             | bool       | Whether to enable external proxy               |
| DBA_ROBOT                         | dict       | DBA robot                      |
| es                                | string     | ES robot                       |
| hdfs                              | string     | HDFS robot                     |
| doris                             | string     | Doris robot                    |
| kafka                             | string     | Kafka robot                    |
| pulsar                            | string     | Pulsar robot                   |
| ENABLE_DBM_AI                     | bool       | Whether to enable DBM AI                 |
| CC_IDLE_MODULE_ID                 | int        | CMDB idle module ID                 |
| BK_COMPONENT_API_URL              | string     | BlueKing component API URL                |
| BK_CMDB_URL                       | string     | BlueKing CMDB URL                   |
| BK_NODEMAN_URL                    | string     | BlueKing node management URL                |
| BK_SCR_URL                        | string     | BlueKing SCR URL                    |
| BKDATA_FRONTEND_REPORT_URL        | string     | BKDATA frontend reporting URL              |
| BK_AIDEV_URL                      | string     | BlueKing AI development URL                  |
| BK_AIDEV_LOG_ANALYSIS_URL         | string     | BlueKing AI development log analysis URL          |
| BKMONITOR_URL                     | string     | BlueKing monitoring URL                    |
| BK_HCM_URL                        | string     | BlueKing HCM URL                    |
| code                              | int        | Response code                         |
| result                            | bool       | Result                           |
| message                           | string     | Message                           |
| request_id                        | string     | Request ID                         |