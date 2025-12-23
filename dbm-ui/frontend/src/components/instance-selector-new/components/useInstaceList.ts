import { getMongoInstancesList } from '@services/source/mongodb';
import { getRedisInstances } from '@services/source/redis';
import { getSqlServerInstanceList as getSqlServerHaInstanceList } from '@services/source/sqlserveHaCluster';
import { getSqlServerInstanceList as getSqlServerSingleInstanceList } from '@services/source/sqlserverSingleCluster';
import { getTendbclusterInstanceList } from '@services/source/tendbcluster';
import { getTendbhaInstanceList } from '@services/source/tendbha';
import { getTendbsingleInstanceList } from '@services/source/tendbsingle';

import { ClusterTypes } from '@common/const';

export const dataSourceMap = {
  [ClusterTypes.MONGO_REPLICA_SET]: getMongoInstancesList,
  [ClusterTypes.MONGO_SHARED_CLUSTER]: getMongoInstancesList,
  [ClusterTypes.REDIS]: getRedisInstances,
  [ClusterTypes.SQLSERVER_HA]: getSqlServerHaInstanceList,
  [ClusterTypes.SQLSERVER_SINGLE]: getSqlServerSingleInstanceList,
  [ClusterTypes.TENDBCLUSTER]: getTendbclusterInstanceList,
  [ClusterTypes.TENDBHA]: getTendbhaInstanceList,
  [ClusterTypes.TENDBSINGLE]: getTendbsingleInstanceList,
} as const;

export default <T extends keyof typeof dataSourceMap>(clusterType: T): (typeof dataSourceMap)[T] =>
  dataSourceMap[clusterType];
