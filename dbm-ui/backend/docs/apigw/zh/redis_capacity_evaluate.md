### 描述

Redis性能容量评估接口

### 请求头
| 参数名          | 类型   | 必填 | 说明               |
|----------------|--------|------|--------------------|
| Content-Type   | string | 是   | 固定值：`application/json` |
| Authorization  | string | 是   | Bearer Token认证   |

## 3. 请求参数
### 3.1 action_info 对象
| 参数名          | 类型   | 必填 | 说明                                                                 | 示例值                          |
|----------------|--------|------|----------------------------------------------------------------------|---------------------------------|
| bk_biz_id      | int    | 是   | 业务ID                                                              | `3`                            |
| action_id      | string | 是   | 操作唯一标识                        | `"xxx0001"`        |
| action_name    | string | 是   | 操作描述                                                            | `"xxxx"`            |
| action_user    | string | 是   | 活动发起人                                                          | `"xiaowang"`                      |
| start_time     | string | 是   | 生效开始时间（ISO8601格式）                                         | `"2025-09-09T06:11:52.773Z"`   |
| end_time       | string | 是   | 生效结束时间（ISO8601格式）                                         | `"2025-09-19T06:11:52.773Z"`   |
| is_force       | int    | 是   | 强制模式：<br>`0`-正常流程，`1`-跳过审批                             | `0`                            |
| user           | string | 是   | 操作人，修改数据的人，或者点确认的人                             | `"operator"`                   |
| approved_user  | string | 否   | 保留字段，请设置为空                                        | `"approver"`                   |

### 3.2 req 数组（集群配置）
| 参数名                                   | 类型   | 必填 | 说明                                                                 | 示例值                          |
|-----------------------------------------|--------|------|----------------------------------------------------------------------|---------------------------------|
| app_type                                | string | 是   | 应用类型标识                                                         | `"default,idip-redis,task-redis,act-redis,具体看后面的app_type段落"`                        |
| cluster_domain                          | string | 是   | 集群完整域名                                                        | `"cache001.xxx.xxx.db"`      |
| req_capacity_m                          | int    | 否   | 扩容容量（MB），与`req_capacity_g`二选一                            | `0`                             |
| req_capacity_g                          | int    | 否   | 扩容容量（GB），与`req_capacity_m`二选一                            | `3`                             |
| req_qps_k                               | int    | 是   | 目标QPS（千次/秒）                                                  | `3`                             |
| req_flag_no_big_key_with_a_lot_of_member| int    | 是   | 大键多成员检查：<br>`0`-不检查，`1`-检查                            | `0`                             |
| req_flag_no_big_value                   | int    | 是   | 大值检查：<br>`0`-不检查，`1`-检查                                   | `0`                             |
| req_flag_no_big_result                  | int    | 是   | 大结果集检查：<br>`0`-不检查，`1`-检查                               | `0`                             |
| req_flag_no_hot_key                     | int    | 是   | 热键检查：<br>`0`-不检查，`1`-检查                                   | `0`                             |
| req_flag_no_use_dns                     | int    | 是   | 热键检查：<br>`0`-不检查，`1`-检查                                   | `0`                             |
| key_pattern                             | array  | 是   | 键模式列表（支持通配符）                                            | `["user:*", "order:*"]`         |

### app_type 应用类型
不同的应用类型对应不同的评估公式。
idip-redis,task-redis,act-redis
todo 补充每种app_type的评估公式

## 4. 请求示例
```json
{
  "action_info": {
    "bk_biz_id": 3,
    "action_id": "xxxxx",
    "action_name": "xxxxxx",
    "action_user": "admin",
    "start_time": "2025-09-09T06:11:52.773Z",
    "end_time": "2025-09-19T06:11:52.773Z",
    "is_force": 0,
    "user": "operator",
    "approved_user": "approver"
  },
  "req": [
    {
      "app_type": "hulk",
      "cluster_domain": "xxx.xx.xx.db",
      "req_capacity_m": 0,
      "req_capacity_g": 3,
      "req_qps_k": 3,
      "req_flag_no_big_key_with_a_lot_of_member": 0,
      "req_flag_no_big_value": 0,
      "req_flag_no_big_result": 0,
      "req_flag_no_hot_key": 0,
      "req_flag_no_use_dns": 0,
      "key_pattern": ["user:*", "order:*"]
    }
  ]
}
                         


### 调用示例
```python
from bkapi.bkdbm.shortcuts import get_client_by_request

client = get_client_by_request(request)
result = client.api.api_test({}, path_params={}, headers=None, verify=True)
```

### 响应示例
```python
{
  "bk_biz_id": 3,
  "time_elapsed_second": 1.01,
  "result_code": 1,
  "result_status": "success",
  "result_msg": "1个评估需求,全部评估通过, 耗时1.01秒",
  "result_detail": [
    {
      "status": "success",
      "message": "评估通过",
      "approved_user": "system",
      "time_elapsed_ms": 1013,
      "cluster_domain": "x.x.x.db",
      "proxy_approve_ok": true,
      "proxy_approve_info": "Proxy:2个,每个可支持Qps:20K, 总共可支持Qps:40K; 总qps需求:3K",
      "backend_approve_ok": true,
      "backend_approve_info": "后端规格:[2c3.5g98gx1;2c3.6g98gx2]x3,每分片可支持Qps:360K, 总共可支持Qps:1080K; 总qps需求:3K",
      "capacity_approve_ok": true,
      "capacity_approve_info": "总容量:10G,剩余容量:7G; 总容量需求:3.0G",
      "related_records_info": "相关记录: 1 个, 总qps需求: 3K, 总容量需求: 3.0G",
      "related_records": {
        "req_qps_k_total": 3,
        "req_capacity_m_total": 3072,
        "req_num": 1,
        "req_list": [
          "string"
        ]
      }
    }
  ]
}
```

### 响应参数说明
 | 参数名               | 类型    | 描述         |
 |---------------------|---------|-------------|
 | bk_biz_id           | int     | 业务ID       |
 | time_elapsed_second | float   | 耗时（秒）   |
 | result_code         | int     | 结果代码,1表示成功,0为失败     |
 | result_status       | string  | 结果状态,success,failed,error     |
 | result_msg          | string  | 结果消息     |
 | result_detail       | array   | 结果详细列表  |
 
##### result_detail 数组元素
 | 参数名                | 类型    | 描述                                 |
 |----------------------|---------|-------------------------------------|
 | status               | string  | 状态, 1：成功，2：失败，3：出错                               |
 | message              | string  | 消息                               |
 | approved_user        | string  | 审批用户                           |
 | time_elapsed_ms      | int     | 耗时（毫秒）                       |
 | cluster_domain       | string  | 集群域名                           |
 | proxy_approve_ok     | bool    | proxy审批是否通过                 |
 | proxy_approve_info   | string  | proxy审批信息                     |
 | backend_approve_ok   | bool    | 后端审批是否通过                   |
 | backend_approve_info | string  | 后端审批信息                       |
 | capacity_approve_ok  | bool    | 容量审批是否通过                   |
 | capacity_approve_info| string  | 容量审批信息                       |
 | related_records_info | string  | 相关记录信息                       |
 | related_records      | object  | 相关记录详情（见下方related_records表格） |

##### related_records 对象字段
 | 参数名               | 类型   | 描述                |
 |---------------------|--------|---------------------|
 | req_qps_k_total     | int    | 总QPS需求（千）     |
 | req_capacity_m_total| int    | 总容量需求（MB）    |
 | req_num             | int    | 需求数量            |
 | req_list            | array  | 需求列表（字符串数组）|