### 描述

这是一个描述

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| id         | int       | 否     | 集群id     |
| name         | string       | 否     | 集群名称     |
| instance         | string       | 否     | 实例     |
| domain         | string       | 否     | 域名     |
| creator         | string       | 否     | 创建人     |
| major_version         | string       | 否     | 主版本号     |
| region         | string       | 否     | 地域     |
| city         | string       | 否     | 城市     |
| cluster_ids         | list[int]       | 否     | 集群id列表     |
| exact_domain         | string       | 否     | 精确域名查询     |
| status         | string       | 否     | 状态     |
| db_module_id         | string       | 否     | 所属DB模块     |
| bk_cloud_id         | string       | 否     | 管控区域     |
| cluster_type         | string       | 否     | 集群类型     |
| ordering         | string       | 否     | 排序字段     |


### 调用示例
```python
from bkapi.bkdbm.shortcuts import get_client_by_request

client = get_client_by_request(request)
result = client.api.api_test({}, path_params={}, headers=None, verify=True)
```

### 响应示例
```python
{
        "id": 130,	//集群id
        "phase": "online",	//集群阶段状态
        "phase_name": "正常",
        "status": "normal",		//集群状态
        "operations": [      //变更记录
          {
            "operator": "admin",
            "cluster_id": 130,
            "flow_id": 6796,    //流程id
            "ticket_id": 2613,	//单据id
            "ticket_type": "REDIS_SCALE_UPDOWN",  //单据类型
            "title": "Redis 集群容量变更",
            "status": "RUNNING"
          }
        ],
        "cluster_time_zone": "+08:00",   //集群所在的时区
        "cluster_name": "kiotest-iam-1",   //集群名称
        "cluster_alias": "kiotest-iam-1",	//集群别名
        "cluster_access_port": 50000,	//集群访问端口
        "cluster_stats": {			//集群状态缓存key
          "total": 3774746624
        },
        "cluster_type": "TwemproxyRedisInstance",	//集群类型
        "cluster_type_name": "TendisCache集群",	//集群类型名
        "disaster_tolerance_level": "CROS_SUBZONE",   //容灾级别
        "master_domain": "cache.kiotest-iam-1.dba.db",  //主域名
        "slave_domain": "",	//从域名
        "cluster_entry": [    //集群访问入口
          {
            "cluster_entry_type": "dns",   //访问类型
            "entry": "cache.kiotest-iam-1.dba.db",   
            "role": "master_entry"  //访问角色  [master_entry/slave_entry:主域名/从域名访问]
          }
        ],
        "bk_biz_id": 3,    //业务id
        "bk_biz_name": "DBA",   
        "bk_cloud_id": 0,   //云区域id
        "bk_cloud_name": "直连区域",
        "major_version": "Redis-5",    //主版本号
        "region": "default",   //地域
        "city": "default",
        "db_module_name": "",    //db模块名称
        "db_module_id": 0,	//模块id
        "creator": "admin",
        "updater": "admin",
        "create_at": "2024-05-14T17:20:23+08:00",
        "update_at": "2024-05-14T17:20:24+08:00",
        "cluster_spec": {    //集群规格
          "creator": "admin",
          "updater": "admin",
          "spec_id": 333,	
          "spec_name": "无限制",
          "spec_cluster_type": "redis",    //集群类型
          "spec_machine_type": "TwemproxyRedisInstance",    //集群规格类型
          "cpu": {
            "max": 256,
            "min": 1
          },
          "mem": {
            "max": 256,
            "min": 1
          },
          "device_class": [],     //设备类型
          "storage_spec": [     //资源规格参数 
            {
              "size": 10,
              "type": "ALL",
              "mount_point": "/data"
            }
          ],
          "desc": "111",
          "enable": true,
          "instance_num": 0,   //实例数
          "qps": {}
        },
        "cluster_capacity": 128.5,    //集群容量
        "dns_to_clb": false,    //dns是否指向clb
        "proxy": [	//代理服务实例
          {
            "name": "",
            "ip": "0.0.0.0",
            "port": 50000,
            "instance": "0.0.0.0:50000",
            "status": "running",
            "version": "",
            "phase": "online",
            "bk_instance_id": 7971,
            "bk_host_id": 490,
            "bk_cloud_id": 0,
            "spec_config": {
              "id": 338,
              "cpu": {
                "max": 2,
                "min": 2
              },
              "mem": {
                "max": 4,
                "min": 3
              },
              "qps": {},
              "name": "2c_4g_50g",
              "count": 2,
              "device_class": [
                "S5.MEDIUM4",
                "SA2.MEDIUM4",
                "S5t.MEDIUM4"
              ],
              "storage_spec": [
                {
                  "size": 50,
                  "type": "ALL",
                  "mount_point": "/data"
                }
              ]
            },
            "bk_sub_zone": "",
            "bk_biz_id": 3,
            "admin_port": 51000
          },
          {
            "name": "",
            "ip": "0.0.0.0",
            "port": 50000,
            "instance": "0.0.0.0:50000",
            "status": "running",
            "version": "",
            "phase": "online",
            "bk_instance_id": 7970,
            "bk_host_id": 489,
            "bk_cloud_id": 0,
            "spec_config": {
              "id": 338,
              "cpu": {
                "max": 2,
                "min": 2
              },
              "mem": {
                "max": 4,
                "min": 3
              },
              "qps": {},
              "name": "2c_4g_50g",
              "count": 2,
              "device_class": [
                "S5.MEDIUM4",
                "SA2.MEDIUM4",
                "S5t.MEDIUM4"
              ],
              "storage_spec": [
                {
                  "size": 50,
                  "type": "ALL",
                  "mount_point": "/data"
                }
              ]
            },
            "bk_sub_zone": "",
            "bk_biz_id": 3,
            "admin_port": 51000
          }
        ],
        "redis_master": [    
          {
            "name": "",
            "ip": "0.0.0.0",
            "port": 30000,
            "instance": "0.0.0.0:30000",
            "status": "running",
            "version": "",
            "phase": "online",
            "bk_instance_id": 7975,
            "bk_host_id": 493,
            "bk_cloud_id": 0,
            "spec_config": {
              "id": 333,
              "cpu": {
                "max": 256,
                "min": 1
              },
              "mem": {
                "max": 256,
                "min": 1
              },
              "qps": {},
              "name": "无限制",
              "count": 1,
              "device_class": [],
              "storage_spec": [
                {
                  "size": 10,
                  "type": "ALL",
                  "mount_point": "/data"
                }
              ]
            },
            "bk_sub_zone": "",   //园区
            "bk_biz_id": 3,
            "is_stand_by": true,
            "seg_range": "0-104999"   //集群分片信息
          }
        ],
        "redis_slave": [
          {
            "name": null,
            "ip": "0.0.0.0",
            "port": 30000,
            "instance": "0.0.0.0:30000",
            "status": "unavailable",  
            "version": null,
            "phase": "online",
            "bk_instance_id": 7979,
            "bk_host_id": 495,
            "bk_cloud_id": 0,
            "spec_config": {
              "id": 333,
              "cpu": {
                "max": 256,
                "min": 1
              },
              "mem": {
                "max": 256,
                "min": 1
              },
              "qps": {},
              "name": "无限制",
              "count": 1,
              "device_class": [],
              "storage_spec": [
                {
                  "size": 10,
                  "type": "ALL",
                  "mount_point": "/data"
                }
              ]
            },
            "bk_sub_zone": "",
            "bk_biz_id": 3,
            "is_stand_by": true,
            "seg_range": "0-104999"
          }
        ],
        "cluster_shard_num": 4,  // 集群分片数
        "machine_pair_cnt": 1,	//机器组数
        "module_names": [],   //db模块名称
        "permission": {
          "redis_keys_delete": true,
          "redis_keys_extract": true,
          "redis_plugin_create_clb": true,
          "redis_plugin_dns_bind_clb": true,
          "redis_plugin_create_polaris": true,
          "redis_destroy": true,
          "redis_open_close": true,
          "redis_purge": true,
          "redis_view": true,
          "redis_backup": true,
          "redis_access_entry_view": true,
          "redis_webconsole": true
        }
      }
```

### 响应参数说明
| 参数名称     | 参数类型   | 描述                           |
| ------------ | ---------- | ------------------------------ |
|              |            |                                |