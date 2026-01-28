import { findRelatedClustersByClusterIds as findMongodbRelatedClustersByClusterIds } from '@services/source/mongodb';
import { findRelatedClustersByClusterIds as findMysqlRelatedClustersByClusterIds } from '@services/source/mysqlCluster';
import { findRelatedClustersByClusterIds as findRedisRelatedClustersByClusterIds } from '@services/source/redisToolbox';
import { findRelatedClustersByClusterIds as findSqlserverRelatedClustersByClusterIds } from '@services/source/sqlserverCluster';

import { ClusterTypes } from '@common/const';

const dataSourceMap = {
  [ClusterTypes.MONGO_REPLICA_SET]: findMongodbRelatedClustersByClusterIds,
  [ClusterTypes.REDIS]: findRedisRelatedClustersByClusterIds,
  [ClusterTypes.REDIS_INSTANCE]: findRedisRelatedClustersByClusterIds,
  [ClusterTypes.SQLSERVER_HA]: findSqlserverRelatedClustersByClusterIds,
  [ClusterTypes.TENDBHA]: findMysqlRelatedClustersByClusterIds,
  [ClusterTypes.TENDBSINGLE]: findMysqlRelatedClustersByClusterIds,
} as const;

export type ISurpportClusterTypes = keyof typeof dataSourceMap;

export default <T extends keyof typeof dataSourceMap>(clusterType: T): (typeof dataSourceMap)[T] =>
  dataSourceMap[clusterType];
