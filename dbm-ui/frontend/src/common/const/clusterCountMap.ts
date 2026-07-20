import { ClusterTypes } from './clusterTypes';
import { DBTypes } from './dbTypes';

/**
 * db集群数量和cluster type的映射
 */
export const ClusterCountMap: Record<string, string[]> = {
  [DBTypes.MONGODB]: [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER],
  [DBTypes.MYSQL]: [ClusterTypes.TENDBSINGLE, ClusterTypes.TENDBHA],
  [DBTypes.ORACLE]: [ClusterTypes.ORACLE_PRIMARY_STANDBY, ClusterTypes.ORACLE_SINGLE_NONE],
  [DBTypes.REDIS]: [ClusterTypes.REDIS_INSTANCE, 'redis_cluster'],
  [DBTypes.SQLSERVER]: [ClusterTypes.SQLSERVER_SINGLE, ClusterTypes.SQLSERVER_HA],
  [DBTypes.TENDBCLUSTER]: [ClusterTypes.TENDBCLUSTER],
};

export const ClusterK8sCountMap: Record<string, string[]> = {
  [DBTypes.K8S_QRRANT]: [ClusterTypes.K8S_QDRANT_HA],
  [DBTypes.K8S_SURREALDB]: [ClusterTypes.K8S_SURREALDB_SINGLE, ClusterTypes.K8S_SURREALDB_HA],
};
