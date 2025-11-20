import { getDorisMachineList } from '@services/source/doris';
import { getEsMachineList } from '@services/source/es';
import { getHdfsMachineList } from '@services/source/hdfs';
import { getKafkaMachineList } from '@services/source/kafka';
import { getMongodbMachineList } from '@services/source/mongodb';
import { getOracleHaMachineList } from '@services/source/oracleHaCluster';
import { getOracleSingleMachineList } from '@services/source/oracleSingleCluster';
import { getPulsarMachineList } from '@services/source/pulsar';
import { getRedisMachineList } from '@services/source/redis';
import { getMachineList as getRiakMachineList } from '@services/source/riak';
import { getMachineList as getSqlserverHaMachineList } from '@services/source/sqlserveHaCluster';
import { getMachineList as getSqlserverSingleMachineList } from '@services/source/sqlserverSingleCluster';
import { getTendbclusterMachineList } from '@services/source/tendbcluster';
import { getTendbhaMachineList } from '@services/source/tendbha';
import { getTendbSingleMachineList } from '@services/source/tendbsingle';

import { ClusterTypes } from '@common/const';

const dataSourceMap = {
  [ClusterTypes.DORIS]: getDorisMachineList,
  [ClusterTypes.ES]: getEsMachineList,
  [ClusterTypes.HDFS]: getHdfsMachineList,
  [ClusterTypes.KAFKA]: getKafkaMachineList,
  [ClusterTypes.MONGO_REPLICA_SET]: getMongodbMachineList,
  [ClusterTypes.MONGO_SHARED_CLUSTER]: getMongodbMachineList,
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: getOracleHaMachineList,
  [ClusterTypes.ORACLE_SINGLE_NONE]: getOracleSingleMachineList,
  [ClusterTypes.PULSAR]: getPulsarMachineList,
  [ClusterTypes.REDIS]: getRedisMachineList,
  [ClusterTypes.REDIS_CLUSTER]: getRedisMachineList,
  [ClusterTypes.REDIS_INSTANCE]: getRedisMachineList,
  [ClusterTypes.RIAK]: getRiakMachineList,
  [ClusterTypes.SQLSERVER_HA]: getSqlserverHaMachineList,
  [ClusterTypes.SQLSERVER_SINGLE]: getSqlserverSingleMachineList,
  [ClusterTypes.TENDBCLUSTER]: getTendbclusterMachineList,
  [ClusterTypes.TENDBHA]: getTendbhaMachineList,
  [ClusterTypes.TENDBSINGLE]: getTendbSingleMachineList,
} as const;

export default <T extends keyof typeof dataSourceMap>(clusterType: T): (typeof dataSourceMap)[T] =>
  dataSourceMap[clusterType];
