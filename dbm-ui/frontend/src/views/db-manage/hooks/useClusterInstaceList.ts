import { getDorisInstanceList } from '@services/source/doris';
import { getEsInstanceList } from '@services/source/es';
import { getHdfsInstanceList } from '@services/source/hdfs';
import { getKafkaInstanceList } from '@services/source/kafka';
import { getMongoInstancesList } from '@services/source/mongodb';
import { getPulsarInstanceList } from '@services/source/pulsar';
import { getRedisInstances } from '@services/source/redis';
import { getRiakInstanceList } from '@services/source/riak';
import { getSqlServerInstanceList as getSqlServerHaInstanceList } from '@services/source/sqlserveHaCluster';
import { getSqlServerInstanceList as getSqlServerSingleInstanceList } from '@services/source/sqlserverSingleCluster';
import { getTendbclusterInstanceList } from '@services/source/tendbcluster';
import { getTendbhaInstanceList } from '@services/source/tendbha';
import { getTendbsingleInstanceList } from '@services/source/tendbsingle';

import { ClusterTypes } from '@common/const';

const dataSourceMap = {
  [ClusterTypes.DORIS]: getDorisInstanceList,
  [ClusterTypes.ES]: getEsInstanceList,
  [ClusterTypes.HDFS]: getHdfsInstanceList,
  [ClusterTypes.KAFKA]: getKafkaInstanceList,
  [ClusterTypes.MONGO_REPLICA_SET]: getMongoInstancesList,
  [ClusterTypes.MONGO_SHARED_CLUSTER]: getMongoInstancesList,
  [ClusterTypes.PULSAR]: getPulsarInstanceList,
  [ClusterTypes.REDIS]: getRedisInstances,
  [ClusterTypes.REDIS_INSTANCE]: getRedisInstances,
  [ClusterTypes.RIAK]: getRiakInstanceList,
  [ClusterTypes.SQLSERVER_HA]: getSqlServerHaInstanceList,
  [ClusterTypes.SQLSERVER_SINGLE]: getSqlServerSingleInstanceList,
  [ClusterTypes.TENDBCLUSTER]: getTendbclusterInstanceList,
  [ClusterTypes.TENDBHA]: getTendbhaInstanceList,
  [ClusterTypes.TENDBSINGLE]: getTendbsingleInstanceList,
} as const;

export default <T extends keyof typeof dataSourceMap>(clusterType: T): (typeof dataSourceMap)[T] =>
  dataSourceMap[clusterType];
