### Functional Description

[Unrelated to business] Query basic information of clusters

### Request Headers

```javascript
'X-Bkapi-Authorization': {"bk_app_code": "abc", "bk_app_secret": "test", "bk_username":"wxid"}
```

- `bk_app_code` and `bk_app_secret` need to be applied for in the BlueKing Developer Center  
- `bk_username`: The username for the call. If it is a platform-level call, a virtual account needs to be applied for in advance  

### Request Parameters

| Field | Type | Required | Description |
| ---- | ---- | ---- | ---- |
| bk_biz_id | int | Yes | Business ID |
| cluster_types | string | No | Cluster type (multiple types separated by commas; enumeration details see below) |
| immute_domain | string | No | Cluster primary domain (supports fuzzy matching) |

#### cluster_type

Below are the enumeration values for cluster types  
```python
1. tendbsingle -- Mysql single-node cluster
2. tendbha -- MySQL high availability cluster
3. tendbcluster -- Spider cluster
4. TwemproxyRedisInstance -- TendisCache cluster
5. TwemproxyTendisSSDInstance -- TendisSSD cluster
6. TwemproxyTendisplusInstance -- Tendis storage version cluster
7. es -- ES cluster
8. kafka -- Kafka cluster
9. hdfs -- Hdfs cluster
10. influxdb -- Influxdb instance
11. pulsar -- Pulsar cluster
12. MongoReplicaSet -- Mongo replica set
13. MongoShardedCluster -- Mongo sharded cluster
14. riak -- Riak cluster
15. sqlserver_single -- sqlserver single-node version
16. sqlserver_ha -- sqlserver master-slave version
```

### Request Parameter Example

```json
{
    "bk_biz_id": 3,
    "immute_domain": "xxxxx"
}
```

### Response Example

```json
[
    {
      "id": 29,
      "name": "xxxxx",
      "bk_biz_id": 3,
      "cluster_type": "kafka",
      "immute_domain": "xxxxxx",
      "major_version": "2.4.0",
      "bk_cloud_id": 0,
      "region": ""
    }
]
```

### Response Parameter Description

| Field | Type | Required | Description |
| ---- | ---- | ---- | ---- |
| id | int | Yes | Cluster ID |
| name | string | Yes | Cluster name |
| bk_biz_id | int | Yes | Business ID |
| cluster_type | string | Yes | Cluster type |
| immute_domain | string | Yes | Cluster primary domain |
| major_version | string | Yes | Cluster version |
| region | string | Yes | City |