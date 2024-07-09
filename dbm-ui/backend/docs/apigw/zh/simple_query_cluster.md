### 功能描述

[不关联业务]查询集群简略信息

### 请求头

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- bk_app_code与bk_app_secret 需要在蓝鲸开发者中心申请
- bk_username：是调用用户名，如果是平台级别的调用需要提前申请虚拟账号


### 请求参数

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| bk_biz_id | int | 是 | 业务ID |
| cluster_types | string | 否 | 集群类型(多个类型用逗号分割，枚举类详见下面) |
| immute_domain | string | 否 | 集群主域名(支持模糊匹配) |

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
    "bk_biz_id"： 3,
    "immute_domain": "kafka.adminxxx.dba.db",
}
```

### 返回结果示例

```json
[
    {
      "id": 29,
      "name": "admin",
      "bk_biz_id": 3,
      "cluster_type": "kafka",
      "immute_domain": "kafka.admin.dba.db",
      "major_version": "2.4.0",
      "bk_cloud_id": 0,
      "region": ""
    }
]
```

### 返回结果参数说明

| 字段 | 类型 | 必选 | 描述 |
| ---- | ---- | ---- | ---- |
| id | int | 是 | 集群ID |
| name | string | 是 | 集群名字 |
| bk_biz_id | int | 是 | 业务ID |
| cluster_type | string | 是 | 集群类型 |
| immute_domain | string | 是 | 集群主域名 |
| major_version | string | 是 | 集群版本 |
| region | string | 是 | 城市 |