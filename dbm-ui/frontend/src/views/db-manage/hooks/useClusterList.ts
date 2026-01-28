import { getDorisList } from '@services/source/doris';
import { getEsList } from '@services/source/es';
import { getHdfsList } from '@services/source/hdfs';
import { getKafkaList } from '@services/source/kafka';
import { getMongoList } from '@services/source/mongodb';
import { getOracleHaClusterList } from '@services/source/oracleHaCluster';
import { getOracleSingleClusterList } from '@services/source/oracleSingleCluster';
import { getPulsarList } from '@services/source/pulsar';
import { getRedisList } from '@services/source/redis';
import { getRiakList } from '@services/source/riak';
import { getHaClusterList as getSqlServerHaClusterList } from '@services/source/sqlserveHaCluster';
import { getSingleClusterList as getSqlServerSingleClusterList } from '@services/source/sqlserverSingleCluster';
import { getTendbClusterList } from '@services/source/tendbcluster';
import { getTendbhaList } from '@services/source/tendbha';
import { getTendbsingleList } from '@services/source/tendbsingle';

import { ClusterTypes } from '@common/const';

const dataSourceMap = {
  [ClusterTypes.DORIS]: getDorisList,
  [ClusterTypes.ES]: getEsList,
  [ClusterTypes.HDFS]: getHdfsList,
  [ClusterTypes.KAFKA]: getKafkaList,
  [ClusterTypes.MONGO_REPLICA_SET]: getMongoList,
  [ClusterTypes.MONGO_SHARED_CLUSTER]: getMongoList,
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: getOracleHaClusterList,
  [ClusterTypes.ORACLE_SINGLE_NONE]: getOracleSingleClusterList,
  [ClusterTypes.PULSAR]: getPulsarList,
  [ClusterTypes.REDIS]: getRedisList,
  [ClusterTypes.REDIS_INSTANCE]: getRedisList,
  [ClusterTypes.RIAK]: getRiakList,
  [ClusterTypes.SQLSERVER_HA]: getSqlServerHaClusterList,
  [ClusterTypes.SQLSERVER_SINGLE]: getSqlServerSingleClusterList,
  [ClusterTypes.TENDBCLUSTER]: getTendbClusterList,
  [ClusterTypes.TENDBHA]: getTendbhaList,
  [ClusterTypes.TENDBSINGLE]: getTendbsingleList,
} as const;

export default <T extends keyof typeof dataSourceMap>(clusterType: T): (typeof dataSourceMap)[T] =>
  dataSourceMap[clusterType];
