import { ClusterTypes } from '@common/const';

// redis
const redisClusterTypePageMap = {
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: 'redisClusterDetail',
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: 'redisClusterDetail',
  [ClusterTypes.REDIS_INSTANCE]: 'redisClusterHaDetail',
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: 'redisClusterDetail',
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: 'redisClusterDetail',
};

// mysql
const mysqlClusterTypePageMap = {
  [ClusterTypes.TENDBHA]: 'tendbHaDetail',
  [ClusterTypes.TENDBSINGLE]: 'tendbsingleDetail',
};

// oracle
const oracleClusterTypePageMap = {
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: 'OracleHaDetail',
  [ClusterTypes.ORACLE_SINGLE_NONE]: 'OracleSingleDetail',
};

// pulsar
const pulsarClusterTypePageMap = {
  [ClusterTypes.PULSAR]: 'PulsarDetail',
};

// riak
const riakClusterTypePageMap = {
  [ClusterTypes.RIAK]: 'riakDetail',
};

// sqlserver
const sqlserverClusterTypePageMap = {
  [ClusterTypes.SQLSERVER_HA]: 'SqlServerHaClusterDetail',
  [ClusterTypes.SQLSERVER_SINGLE]: 'SqlServerSingleClusterDetail',
};

// tendbcluster
const tendbclusterClusterTypePageMap = {
  [ClusterTypes.TENDBCLUSTER]: 'tendbClusterDetail',
};

// mongodb
const mongodbClusterTypePageMap = {
  [ClusterTypes.MONGO_REPLICA_SET]: 'MongoDBReplicaSetDetail',
  [ClusterTypes.MONGO_SHARED_CLUSTER]: 'MongoDBSharedClusterDetail',
};

// es
const esClusterTypePageMap = {
  [ClusterTypes.ES]: 'esDetail',
};

// hdfs
const hdfsClusterTypePageMap = {
  [ClusterTypes.HDFS]: 'hdfsDetail',
};

// kafka
const kafkaClusterTypePageMap = {
  [ClusterTypes.KAFKA]: 'KafkaDetail',
};

// doris
const dorisClusterTypePageMap = {
  [ClusterTypes.DORIS]: 'DorisDetail',
};

// surrealdb
const surrealdbClusterTypePageMap = {
  [ClusterTypes.K8S_SURREALDB_HA]: 'SurrealdbHaDetail',
  [ClusterTypes.K8S_SURREALDB_SINGLE]: 'SurrealdbSingleDetail',
};

export const clusterTypeListPageMap: Record<string, string> = {
  ...redisClusterTypePageMap,
  ...mysqlClusterTypePageMap,
  ...oracleClusterTypePageMap,
  ...surrealdbClusterTypePageMap,
  ...pulsarClusterTypePageMap,
  ...riakClusterTypePageMap,
  ...sqlserverClusterTypePageMap,
  ...tendbclusterClusterTypePageMap,
  ...esClusterTypePageMap,
  ...hdfsClusterTypePageMap,
  ...kafkaClusterTypePageMap,
  ...mongodbClusterTypePageMap,
  ...dorisClusterTypePageMap,
};
