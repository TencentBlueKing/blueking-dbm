### 描述

查询业务下的集群的详情信息

### headers 
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| Content-Type         | string       | 是     | application/json     |
|X-Bkapi-Authorization | dict | 是 | 包含bk_app_code，bk_app_secret，bk_username|


### 输入参数
| 参数名称     | 参数类型     | 必选   | 描述             |
| ------------ | ------------ | ------ | ---------------- |
| bk_biz_id    | int         | 是     | 业务id           |
| cluster_id   | int         | 是     | 集群id           |



### 调用示例
```python
curl -X 'GET' \
  'http://example.com/apis/mysql/bizs/3/spider_resources/1000072/' \
  -H 'accept: application/json' \
  -H 'X-CSRFTOKEN: xxxxxx' \
  -H 'X-Bkapi-Authorization: {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}'

```

### 响应示例
```python
{
	"data": {
		"id": 1000072,
		"db_type": "tendbcluster",
		"phase": "online",
		"phase_name": "正常",
		"status": "normal",
		"operations": [{
				"operator": "admin",
				"cluster_id": 1000072,
				"flow_id": 8851,
				"ticket_id": 3071,
				"ticket_type": "TENDBCLUSTER_CHECKSUM",
				"title": "TenDB Cluster 数据校验修复",
				"status": "FAILED"
			}
		],
		"dns_to_clb": false,
		"cluster_time_zone": "+08:00",
		"cluster_name": "cwntest",
		"cluster_alias": "test1",
		"cluster_access_port": 25000,
		"cluster_stats": {},
		"cluster_type": "tendbcluster",
		"cluster_type_name": "TendbCluster集群",
		"cluster_subzones": [],
		"cluster_subzone_ids": [],
		"disaster_tolerance_level": "NONE",
		"master_domain": "spider.cwntest.dba.db",
		"slave_domain": "",
		"cluster_entry": [{
			"cluster_entry_type": "dns",
			"entry": "spider.cwntest.dba.db",
			"role": "master_entry"
		}],
		"bk_biz_id": 3,
		"bk_biz_name": "DBA",
		"bk_cloud_id": 0,
		"bk_cloud_name": "直连区域",
		"major_version": "MySQL-5.6",
		"region": "default",
		"city": "default",
		"db_module_name": "tes",
		"db_module_id": 26,
		"creator": "admin",
		"updater": "v_ycggyao",
		"create_at": "2025-07-11T18:24:45+08:00",
		"update_at": "2025-08-08T09:59:44+08:00",
		"cluster_spec": {
			"creator": "admin",
			"updater": "admin",
			"spec_id": 439,
			"spec_name": "remote通用",
			"spec_cluster_type": "tendbcluster",
			"spec_machine_type": "backend",
			"cpu": {
				"max": 256,
				"min": 1
			},
			"mem": {
				"max": 2048,
				"min": 1
			},
			"device_class": [],
			"storage_spec": [{
				"max": 2147483647,
				"min": 10,
				"size": 10,
				"type": "ALL",
				"mount_point": "/data"
			}],
			"desc": "",
			"enable": true,
			"biz_scope": [],
			"instance_num": 0,
			"qps": {
				"max": 0,
				"min": 0
			},
			"id": 439
		},
		"tags": [],
		"zone_list": null,
		"cluster_capacity": 5,
		"spider_master": [{
				"name": "",
				"ip": "0.0.0.0",
				"port": 25000,
				"instance": "0.0.0.0:25000",
				"status": "running",
				"version": "3.7.8",
				"phase": "online",
				"bk_instance_id": 14547,
				"bk_host_id": 24,
				"bk_cloud_id": 0,
				"spec_config": {
					"id": 440,
					"cpu": {
						"max": 256,
						"min": 1
					},
					"mem": {
						"max": 2048,
						"min": 1
					},
					"qps": {
						"max": 0,
						"min": 0
					},
					"name": "spider通用",
					"count": 2,
					"device_class": [],
					"storage_spec": [{
						"size": 10,
						"type": "ALL",
						"mount_point": "/data"
					}]
				},
				"bk_sub_zone": "",
				"bk_biz_id": 3,
				"bk_rack_id": 0,
				"admin_port": 26000
			}
		],
		"spider_slave": [],
		"spider_mnt": [],
		"cluster_shard_num": 4,
		"remote_shard_num": 4,
		"machine_pair_cnt": 1,
		"remote_db": [{
				"name": "",
				"ip": "0.0.0.0",
				"port": 20000,
				"instance": "0.0.0.0:20000",
				"status": "running",
				"version": "5.6.24",
				"phase": "online",
				"bk_instance_id": 14539,
				"bk_host_id": 449,
				"bk_cloud_id": 0,
				"spec_config": {
					"id": 439,
					"cpu": {
						"max": 256,
						"min": 1
					},
					"mem": {
						"max": 2048,
						"min": 1
					},
					"qps": {
						"max": 0,
						"min": 0
					},
					"name": "remote通用",
					"count": 1,
					"device_class": [],
					"storage_spec": [{
						"size": 10,
						"type": "ALL",
						"mount_point": "/data"
					}]
				},
				"bk_sub_zone": "",
				"bk_biz_id": 3,
				"bk_rack_id": 0,
				"is_stand_by": true,
				"shard_id": 0
			}
		],
		"remote_dr": [{
				"name": "",
				"ip": "0.0.0.0",
				"port": 20000,
				"instance": "0.0.0.0:20000",
				"status": "running",
				"version": "5.6.24",
				"phase": "online",
				"bk_instance_id": 14540,
				"bk_host_id": 856,
				"bk_cloud_id": 0,
				"spec_config": {
					"id": 439,
					"cpu": {
						"max": 256,
						"min": 1
					},
					"mem": {
						"max": 2048,
						"min": 1
					},
					"qps": {
						"max": 0,
						"min": 0
					},
					"name": "remote通用",
					"count": 1,
					"device_class": [],
					"storage_spec": [{
						"size": 10,
						"type": "ALL",
						"mount_point": "/data"
					}]
				},
				"bk_sub_zone": "",
				"bk_biz_id": 3,
				"bk_rack_id": 0,
				"is_stand_by": true,
				"shard_id": 0
			}
		],
		"temporary_info": {},
		"cluster_entry_details": [{
			"cluster_entry_type": "dns",
			"role": "master_entry",
			"entry": "spider.cwntest.dba.db",
			"target_details": [{
					"app": "3",
					"bk_cloud_id": 0,
					"dns_str": "",
					"domain_name": "spider.cwntest.dba.db.",
					"domain_type": 0,
					"ip": "0.0.0.0",
					"last_change_time": "2025-07-11T18:23:59+08:00",
					"manager": "DBAManager",
					"port": 25000,
					"remark": "",
					"start_time": "2025-07-11T18:23:59+08:00",
					"status": "1",
					"uid": 5308
				},
				{
					"app": "3",
					"bk_cloud_id": 0,
					"dns_str": "",
					"domain_name": "spider.cwntest.dba.db.",
					"domain_type": 0,
					"ip": "0.0.0.0",
					"last_change_time": "2025-07-11T18:23:59+08:00",
					"manager": "DBAManager",
					"port": 25000,
					"remark": "",
					"start_time": "2025-07-11T18:23:59+08:00",
					"status": "1",
					"uid": 5309
				}
			],
			"instance_role": null
		}],
		"spider_ctl_primary": "0.0.0.0:26000",
		"permission": {
			"tendbcluster_view": true,
			"tendbcluster_edit": true,
			"tendb_spider_slave_destroy": true,
			"tendbcluster_enable_disable": true,
			"tendbcluster_add_clb": true,
			"tendbcluster_clb_bind_domain": true,
			"tendbcluster_webconsole": true,
			"tendbcluster_destroy": true,
			"tendbcluster_spider_add_nodes": true,
			"tendbcluster_spider_reduce_nodes": true,
			"tendbcluster_spider_mnt_destroy": true,
			"tendbcluster_node_rebalance": true,
			"tendbcluster_dump_data": true,
			"tendbcluster_subscribe_monitor": true
		}
	},
	"code": 0,
	"result": true,
	"message": "OK",
	"request_id": "9d11652423c14282bdd64f423be5af50"
}
```

### 响应参数说明
| 参数名称                  | 参数类型   | 描述                           |
| ------------------------- | ---------- | ------------------------------ |
| data                      | dict       | 数据                           |
| id                        | int        | 集群id                         |
| db_type                   | string     | 数据库类型                     |
| phase                     | string     | 阶段                           |
| phase_name                | string     | 阶段名称                       |
| status                    | string     | 状态                           |
| operations                | list       | 操作记录列表                   |
| dns_to_clb                | bool       | 是否DNS到CLB                   |
| cluster_time_zone         | string     | 集群时区                       |
| cluster_name              | string     | 集群名称                       |
| cluster_alias             | string     | 集群别名                       |
| cluster_access_port       | int        | 集群访问端口                   |
| cluster_stats             | dict       | 集群统计信息                   |
| cluster_type              | string     | 集群类型                       |
| cluster_type_name         | string     | 集群类型名称                   |
| cluster_subzones          | list       | 集群子分区列表                 |
| cluster_subzone_ids       | list       | 集群子分区id列表               |
| disaster_tolerance_level  | string     | 容灾等级                       |
| master_domain             | string     | 主域名                         |
| slave_domain              | string     | 从域名                         |
| cluster_entry             | list       | 集群入口列表                   |
| bk_biz_id                 | int        | 业务id                         |
| bk_biz_name               | string     | 业务名称                       |
| bk_cloud_id               | int        | 云区域id                       |
| bk_cloud_name             | string     | 云区域名称                     |
| major_version             | string     | 主版本                         |
| region                    | string     | 区域                           |
| city                      | string     | 城市                           |
| db_module_name            | string     | 数据库模块名称                 |
| db_module_id              | int        | 数据库模块id                   |
| creator                   | string     | 创建人                         |
| updater                   | string     | 更新人                         |
| create_at                 | string     | 创建时间                       |
| update_at                 | string     | 更新时间                       |
| cluster_spec              | dict       | 集群规格配置                   |
| tags                      | list       | 标签列表                       |
| zone_list                 | string     | 区域列表                       |
| cluster_capacity          | int        | 集群容量                       |
| spider_master             | list       | Spider主节点列表               |
| spider_slave              | list       | Spider从节点列表               |
| spider_mnt                | list       | Spider挂载节点列表             |
| cluster_shard_num         | int        | 集群分片数                     |
| remote_shard_num          | int        | 远程分片数                     |
| machine_pair_cnt          | int        | 机器对数                       |
| remote_db                 | list       | 远程数据库列表                 |
| remote_dr                 | list       | 远程容灾节点列表               |
| temporary_info            | dict       | 临时信息                       |
| cluster_entry_details     | list       | 集群入口详情列表               |
| spider_ctl_primary        | string     | Spider控制主节点               |
| permission                | dict       | 权限信息                       |
| code                      | int        | 响应码                         |
| result                    | bool       | 结果                           |
| message                   | string     | 消息                           |
| request_id                | string     | 请求id                         |