import { ClusterTypes } from './clusterTypes';
import { DBTypes } from './dbTypes';

/**
 * db类型关联集群类型集合映射关系
 */
export const queryClusterTypes = {
  [DBTypes.DORIS]: [ClusterTypes.DORIS],
  [DBTypes.ES]: [ClusterTypes.ES],
  [DBTypes.HDFS]: [ClusterTypes.HDFS],
  [DBTypes.INFLUXDB]: [ClusterTypes.INFLUXDB],
  [DBTypes.K8S_QRRANT]: [ClusterTypes.K8S_QDRANT_HA],
  [DBTypes.K8S_SURREALDB]: [ClusterTypes.K8S_SURREALDB_SINGLE, ClusterTypes.K8S_SURREALDB_HA],
  [DBTypes.KAFKA]: [ClusterTypes.KAFKA],
  [DBTypes.MONGODB]: [ClusterTypes.MONGODB, ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
  [DBTypes.MYSQL]: [ClusterTypes.TENDBSINGLE, ClusterTypes.TENDBHA],
  [DBTypes.ORACLE]: [ClusterTypes.ORACLE_PRIMARY_STANDBY, ClusterTypes.ORACLE_SINGLE_NONE],
  [DBTypes.PULSAR]: [ClusterTypes.PULSAR],
  [DBTypes.REDIS]: [
    ClusterTypes.REDIS,
    ClusterTypes.PREDIXY_REDIS_CLUSTER,
    ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE,
    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    ClusterTypes.TWEMPROXY_TENDISPLUS_INSTANCE,
    ClusterTypes.REDIS_INSTANCE,
    ClusterTypes.TENDIS_SSD_INSTANCE,
    ClusterTypes.TENDIS_PLUS_INSTANCE,
    ClusterTypes.REDIS_CLUSTER,
    ClusterTypes.TENDIS_PLUS_CLUSTER,
  ],
  [DBTypes.RIAK]: [ClusterTypes.RIAK],
  [DBTypes.SQLSERVER]: [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE],
  [DBTypes.TENDBCLUSTER]: [ClusterTypes.TENDBCLUSTER],
};
