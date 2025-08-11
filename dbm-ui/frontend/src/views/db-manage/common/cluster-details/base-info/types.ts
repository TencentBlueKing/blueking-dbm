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
import RedisModelDetail from '@services/model/redis/redis-detail';
import RiakModelDetail from '@services/model/riak/riak-detail';
import SqlserverHaModelDetail from '@services/model/sqlserver/sqlserver-ha-detail';
import SqlserverSingleModelDetail from '@services/model/sqlserver/sqlserver-single-detail';
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
  | ClusterTypes.REDIS
  | ClusterTypes.REDIS_INSTANCE
  | ClusterTypes.RIAK
  | ClusterTypes.KAFKA
  | ClusterTypes.SQLSERVER_HA
  | ClusterTypes.SQLSERVER_SINGLE
  | ClusterTypes.MONGO_REPLICA_SET
  | ClusterTypes.MONGO_SHARED_CLUSTER
  | ClusterTypes.ORACLE_PRIMARY_STANDBY
  | ClusterTypes.ORACLE_SINGLE_NONE;

export interface ClusterTypeRelateClusterModelDetail {
  [ClusterTypes.DORIS]: DorisModelDetail;
  [ClusterTypes.ES]: EsModelDetail;
  [ClusterTypes.HDFS]: HdfsModelDetail;
  [ClusterTypes.KAFKA]: KafkaModelDetail;
  [ClusterTypes.MONGO_REPLICA_SET]: MongodbModelDetail;
  [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbModelDetail;
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: OracleHaModelDetail;
  [ClusterTypes.ORACLE_SINGLE_NONE]: OracleSingleModelDetail;
  [ClusterTypes.PULSAR]: PulsarModelDetail;
  [ClusterTypes.REDIS_INSTANCE]: RedisModelDetail;
  [ClusterTypes.REDIS]: RedisModelDetail;
  [ClusterTypes.RIAK]: RiakModelDetail;
  [ClusterTypes.SQLSERVER_HA]: SqlserverHaModelDetail;
  [ClusterTypes.SQLSERVER_SINGLE]: SqlserverSingleModelDetail;
  [ClusterTypes.TENDBCLUSTER]: TendbClusterModelDetail;
  [ClusterTypes.TENDBHA]: TendbhaModelDetail;
  [ClusterTypes.TENDBSINGLE]: TendbsingleModelDetail;
}

export type ClusterDetailModel<T extends keyof ClusterTypeRelateClusterModelDetail> =
  ClusterTypeRelateClusterModelDetail[T];
