import DorisModelDetail from '@services/model/doris/doris-detail';
import EsModelDetail from '@services/model/es/es-detail';
import HdfsModelDetail from '@services/model/hdfs/hdfs-detail';
import KafkaModelDetail from '@services/model/kafka/kafka-detail';
import MongodbModelDetail from '@services/model/mongodb/mongodb-detail';
import TendbhaModelDetail from '@services/model/mysql/tendbha-detail';
import TendbsingleModelDetail from '@services/model/mysql/tendbsingle-detail';
import OracleHaModelDetail from '@services/model/oracle/oracle-ha-detail';
import OracleSingleModelDetail from '@services/model/oracle/oracle-single-detail';
import PulsarModelDetail from '@services/model/pulsar/pulsar-detail';
import QdrantHaModelDetail from '@services/model/qdrant/qdrant-ha-detail';
import RedisModelDetail from '@services/model/redis/redis-detail';
import RiakModelDetail from '@services/model/riak/riak-detail';
import SqlserverHaModelDetail from '@services/model/sqlserver/sqlserver-ha-detail';
import SqlserverSingleModelDetail from '@services/model/sqlserver/sqlserver-single-detail';
import SurrealdbHaModelDetail from '@services/model/surrealdb/surrealdb-ha-detail';
import SurrealdbSingleModelDetail from '@services/model/surrealdb/surrealdb-single-detail';
import TendbClusterModelDetail from '@services/model/tendbcluster/tendbcluster-detail';

import { ClusterTypes } from '@common/const';

export type ISupportClusterType =
  | ClusterTypes.TENDBCLUSTER
  | ClusterTypes.DORIS
  | ClusterTypes.ES
  | ClusterTypes.HDFS
  | ClusterTypes.TENDBHA
  | ClusterTypes.TENDBSINGLE
  | ClusterTypes.PULSAR
  // | ClusterTypes.REDIS
  | ClusterTypes.REDIS_INSTANCE
  | ClusterTypes.RIAK
  | ClusterTypes.KAFKA
  | ClusterTypes.SQLSERVER_HA
  | ClusterTypes.SQLSERVER_SINGLE
  | ClusterTypes.MONGO_REPLICA_SET
  | ClusterTypes.MONGO_SHARED_CLUSTER
  | ClusterTypes.ORACLE_PRIMARY_STANDBY
  | ClusterTypes.ORACLE_SINGLE_NONE
  | ClusterTypes.PREDIXY_REDIS_CLUSTER
  | ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER
  | ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE
  | ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE
  | ClusterTypes.REDIS_INSTANCE
  | ClusterTypes.TWEMPROXY_REDIS_INSTANCE
  | ClusterTypes.K8S_SURREALDB_HA
  | ClusterTypes.K8S_SURREALDB_SINGLE
  | ClusterTypes.K8S_QDRANT_HA;

export interface ClusterTypeRelateClusterModelDetail {
  [ClusterTypes.DORIS]: DorisModelDetail;
  [ClusterTypes.ES]: EsModelDetail;
  [ClusterTypes.HDFS]: HdfsModelDetail;
  [ClusterTypes.K8S_QDRANT_HA]: QdrantHaModelDetail;
  [ClusterTypes.K8S_SURREALDB_HA]: SurrealdbHaModelDetail;
  [ClusterTypes.K8S_SURREALDB_SINGLE]: SurrealdbSingleModelDetail;
  [ClusterTypes.KAFKA]: KafkaModelDetail;
  [ClusterTypes.MONGO_REPLICA_SET]: MongodbModelDetail;
  [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbModelDetail;
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: OracleHaModelDetail;
  [ClusterTypes.ORACLE_SINGLE_NONE]: OracleSingleModelDetail;
  // [ClusterTypes.REDIS]: RedisModelDetail;
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: RedisModelDetail;
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: RedisModelDetail;
  [ClusterTypes.PREDIXY_TENDISPLUS_INSTANCE]: RedisModelDetail;
  [ClusterTypes.PULSAR]: PulsarModelDetail;
  [ClusterTypes.REDIS_INSTANCE]: RedisModelDetail;
  [ClusterTypes.REDIS_INSTANCE]: RedisModelDetail;
  [ClusterTypes.RIAK]: RiakModelDetail;
  [ClusterTypes.SQLSERVER_HA]: SqlserverHaModelDetail;
  [ClusterTypes.SQLSERVER_SINGLE]: SqlserverSingleModelDetail;
  [ClusterTypes.TENDBCLUSTER]: TendbClusterModelDetail;
  [ClusterTypes.TENDBHA]: TendbhaModelDetail;
  [ClusterTypes.TENDBSINGLE]: TendbsingleModelDetail;
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: RedisModelDetail;
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: RedisModelDetail;
}

export type ClusterDetailModel<T extends keyof ClusterTypeRelateClusterModelDetail> =
  ClusterTypeRelateClusterModelDetail[T];
