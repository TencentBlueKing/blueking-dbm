import { ClusterTypes } from './clusterTypes';
import { DBTypes } from './dbTypes';

/**
 * db类型关联集群类型集合映射关系
 */
export const queryClusterTypes = {
  [DBTypes.MYSQL]: [ClusterTypes.TENDBSINGLE, ClusterTypes.TENDBHA],
  [DBTypes.TENDBCLUSTER]: [ClusterTypes.TENDBCLUSTER],
  [DBTypes.REDIS]: [
    ClusterTypes.REDIS,
    ClusterTypes.PREDIXY_REDIS_CLUSTER,
    ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    ClusterTypes.TWEMPROXY_TENDISPLUS_INSTANCE,
    ClusterTypes.REDIS_INSTANCE,
    ClusterTypes.TENDIS_SSD_INSTANCE,
    ClusterTypes.TENDIS_PLUS_INSTANCE,
    ClusterTypes.REDIS_CLUSTER,
    ClusterTypes.TENDIS_PLUS_CLUSTER,
  ],
  [DBTypes.MONGODB]: [ClusterTypes.MONGODB, ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
  [DBTypes.SQLSERVER]: [ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE],
  [DBTypes.ES]: [ClusterTypes.ES],
  [DBTypes.KAFKA]: [ClusterTypes.KAFKA],
  [DBTypes.HDFS]: [ClusterTypes.HDFS],
  [DBTypes.RIAK]: [ClusterTypes.RIAK],
  [DBTypes.PULSAR]: [ClusterTypes.PULSAR],
  [DBTypes.INFLUXDB]: [ClusterTypes.INFLUXDB],
  [DBTypes.DORIS]: [ClusterTypes.DORIS],
};
