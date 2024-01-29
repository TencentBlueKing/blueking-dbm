
### 功能描述

创建单据

### 请求参数

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| bk_biz_id | int | 是 | 业务ID |
| cluster_types | string | 是 | 集群类型(多个类型用逗号分割，枚举类详见下面) |
| cluster_ids | string | 是 | 集群ID过滤(多个ID用逗号分割) |

#### cluster_type

下面是集群类型的枚举值
```python
1. tendbsingle -- Mysql单节点集群
2. tendbha -- MySQL高可用集群
3. tendbcluster -- Spider集群
4. TwemproxyRedisInstance -- TendisCache集群
5. TwemproxyTendisSSDInstance -- TendisSSD集群
6. TwemproxyTendisplusInstance -- Tendis存储版集群
7. es -- ES集群
8. kafka -- Kafka集群
9. hdfs -- Hdfs集群
10. influxdb -- Influxdb实例
11. pulsar -- Pulsar集群
12. MongoReplicaSet -- Mongo副本集
13. MongoShardedCluster -- Mongo分片集群
14. riak -- Riak集群
15. sqlserver_single -- sqlserver单节点版
16. sqlserver_ha -- sqlserver主从版
```

### 请求参数示例

```json
{
    "bk_biz_id": 3,
    "cluster_type": "tendbha"
}
```

### 返回结果示例

```json
[
    {
        "cluster_id": 96,
        "cluster_name": "xx123-dbha",
        "cluster_alias": "",
        "cluster_type": "tendbha",
        "master_domain": "tendbha57db.xx123.dba.db",
        "slave_domain": "tendbha57dr.xx123.dba.db",
        "major_version": "MySQL-5.7",
        "region": "default",
        "disaster_tolerance_level": "NONE",
        "backend_master": "127.0.0.1#20000",
        "backend_slave": "127.0.0.2#20000",
        "proxy": "1.1.1.1#10000\n2.2.2.2#10000"
    },
    {
        "cluster_id": 72,
        "cluster_name": "xiaogtxsql",
        "cluster_alias": "",
        "cluster_type": "tendbha",
        "master_domain": "mysql80db.xxxx.dba.db",
        "slave_domain": "mysql80dr.xxxx.dba.db",
        "major_version": "MySQL-8.0",
        "region": "",
        "disaster_tolerance_level": "NONE",
        "backend_master": "127.0.0.1#20000",
        "backend_slave": "127.0.0.2#20000",
        "proxy": "1.1.1.1#10000\n2.2.2.2#10000"
    }
]
```

### 返回结果参数说明

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| cluster_id | int | 是 | 集群ID |
| cluster_name | string | 是 | 集群名字 |
| cluster_alias | string | 是 | 集群别名 |
| cluster_type | string | 是 | 集群类型 |
| master_domain | string | 是 | 集群主域名 |
| slave_domain | string | 否 | 集群从域名 |
| major_version | string | 是 | 集群版本 |
| disaster_tolerance_level | string | 是 | 集群容灾要求 |
| role_1 | string | 是 | 集群角色1，多个角色用\\n分割 |
| role_2 | string | 是 | 集群角色2，多个角色用\\n分割 |
| .... | ... | ... | ... |
| role_n | string | 是 | 集群角色n，多个角色用\\n分割 |

#### 集群角色说明
TODO....