# 15 个 DB 的形态矩阵

改某个 DB 之前先在这里定位它的目录名与路由名。路由名要精确，`useGoClusterDetail`、
`clusterTypeListPageMap`、`DBTypeInfos.routeIndexName` 全靠字符串对上。

## 标识与路由

| DB | `DBTypes` | 目录 | `ClusterTypes` | 父路由（= `routeIndexName`） | 集群列表 | 集群详情 | 实例列表 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MySQL | `MYSQL` | `mysql` | `TENDBHA`、`TENDBSINGLE` | `MysqlManage` | `DatabaseTendbha` / `DatabaseTendbsingle` | `tendbHaDetail` / `tendbsingleDetail` | `DatabaseTendbhaInstance` |
| TenDBCluster | `TENDBCLUSTER` | **`tendb-cluster`** | `TENDBCLUSTER` | `SpiderManage` | `tendbClusterList` | `tendbClusterDetail` | `tendbClusterInstance` |
| Redis | `REDIS` | `redis` | `REDIS`（集群版）、`REDIS_INSTANCE`（主从）+ `TWEMPROXY_*` / `PREDIXY_*` | `RedisManage` | `DatabaseRedisList` / `DatabaseRedisHaList` | `redisClusterDetail` / `redisClusterHaDetail` | `DatabaseRedisInstanceList` / `DatabaseRedisHaInstanceList` |
| MongoDB | `MONGODB` | `mongodb` | `MONGO_REPLICA_SET`、`MONGO_SHARED_CLUSTER` | `MongoDBManage` | `MongoDBReplicaSetList` / `MongoDBSharedClusterList` | `MongoDBReplicaSetDetail` / `MongoDBSharedClusterDetail` | `mongodbReplicaSetInstanceList` / `mongodbShareClusterInstanceList` |
| SQLServer | `SQLSERVER` | `sqlserver` | `SQLSERVER_HA`、`SQLSERVER_SINGLE` | `SqlServerManage` | `SqlServerHaClusterList` / `SqlServerSingleClusterList` | `SqlServerHaClusterDetail` / `SqlServerSingleClusterDetail` | `SqlServerHaInstanceList` |
| Oracle | `ORACLE` | `oracle` | `ORACLE_PRIMARY_STANDBY`、`ORACLE_SINGLE_NONE` | `OracleManage` | `OracleHaClusterList` / `OracleSingleClusterList` | `OracleHaDetail` / `OracleSingleDetail` | `OracleHaInstanceList` |
| Doris | `DORIS` | `doris` | `DORIS` | `DorisManage` | `DorisList` | `DorisDetail` | 无 |
| ElasticSearch | `ES` | **`elastic-search`** | `ES` | `EsManage` | `EsList` | `esDetail` | 无 |
| HDFS | `HDFS` | `hdfs` | `HDFS` | `HdfsManage` | `HdfsList` | `hdfsDetail` | 无 |
| Kafka | `KAFKA` | `kafka` | `KAFKA` | `KafkaManage` | `KafkaList` | `KafkaDetail` | 无 |
| Pulsar | `PULSAR` | `pulsar` | `PULSAR` | `PulsarManage` | `PulsarList` | `PulsarDetail` | 无 |
| Riak | `RIAK` | `riak` | `RIAK` | `RiakManage` | `RiakList` | `riakDetail` | 无 |
| InfluxDB | `INFLUXDB` | `influxdb` | `INFLUXDB` | `InfluxDBManage` | 无 | 无 | `InfluxDBInstances`（详情 `InfluxDBInstDetails`） |
| Qdrant | `K8S_QDRANT` | **`qdrant`** | `K8S_QDRANT_HA` | `QdrantManage` | `QdrantHaList` | `QdrantHaDetail` | 无独立页 |
| SurrealDB | `K8S_SURREALDB` | **`surrealdb`** | `K8S_SURREALDB_HA`、`K8S_SURREALDB_SINGLE` | `SurrealDBManage` | `SurrealdbHaList` / `SurrealdbSingleList` | `SurrealdbHaDetail` / `SurrealdbSingleDetail` | 无独立页 |

**加粗的四个是目录名 ≠ `DBTypes` 值的例外**（枚举值分别是 `tendbcluster`、`es`、`k8s_qdrant`、
`k8s_surrealdb`），写路径、写 glob、写 `createApplyRoute` 时都要留意。

路由名大小写不统一（`tendbHaDetail` 与 `SurrealdbHaDetail` 并存）是历史沿革，**照抄，不要顺手改**：
改一处要同步 `clusterTypeListPageMap`、`useGoClusterDetail` 入参、`layout` 菜单 `route-name`、
`DBTypeInfos.routeIndexName`、`layout/Index.vue` 的 `routeGroup` 五处。

## 功能开关 key

读法：`funControllerData.getFlatData<XxxFunctions, 'xxx'>('模块名')`，返回扁平对象，父 key 是模块自身开关，
子 key 是各功能开关。

- mysql / redis / mongodb / sqlserver / oracle：各自一个独立模块，模块名即 `DBTypes` 值
- 大数据 7 个：模块 `bigdata`，子 key 是 `DBTypes` 值（`doris`、`es`…）
- K8s 2 个：模块 `k8s`，子 key 是 `DBTypes` 值（`k8s_qdrant`、`k8s_surrealdb`）
- **TenDBCluster 走 `mysql` 模块，且没有顶层路由开关**，`tendb-cluster/routes.ts` 无条件返回路由

## 能力差异

本篇只管标识与路由。**哪个 DB 有哪项能力、哪些「没有」是设定、抄哪个 DB 当样本，一律看**
[feature-scope.md](feature-scope.md)，不要从上表的架构数量反推。Redis 往映射表填 key 前另看
[registry-map.md](registry-map.md) 的「Redis 的 key」。

## 数据层

`services/source/` 的文件名按架构或按 DB 拆都有（`surrealdbHa.ts` / `surrealdbSingle.ts` 对
`kafka.ts`），`services/model/{db}/` 一律按 DB 建目录。新增时照抄同形态样本，选哪个见
[feature-scope.md](feature-scope.md)。

URL 前缀按后端模块分，不是按 `DBTypes` 拼的，没有统一模板：

- `/apis/mysql/bizs/{bizId}/tendbha_resources`
- `/apis/bigdata/bizs/{bizId}/riak/riak_resources`（大数据多一层组件名）
- `/apis/kubernetes/bizs/{bizId}/qdrantha/qdrantha_resources`
- `/apis/dbbase/...`（跨 DB 通用，靠 query 的 `cluster_type` / `db_type` 区分；`filterClusters`、
  `queryClusterInstanceCount`、`queryBizClusterAttrs`、`updateClusterAlias`、集群标签等都在这）

各 DB 列表行 Model 一律 `extends ClusterBase`（`services/model/_clusterBase.ts`），基类已提供
`isOnline` / `isOffline` / `isNew` / `masterDomain` / `availableTags` / `createAtDisplay`，
**不要在子类里重复实现**。子类只写该 DB 的操作态 getter（`operationTagTips`、`operationDisabled`、
`operationStatusText`、`allInstanceList`、`isAbnormal`），公共组件直接读这些名字，命名照抄同类 DB。
实例 Model 基类是 `_instanceBase.ts`。
