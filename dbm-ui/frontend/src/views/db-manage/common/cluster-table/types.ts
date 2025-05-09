import DorisModel from '@services/model/doris/doris';
import EsModel from '@services/model/es/es';
import HdfsModel from '@services/model/hdfs/hdfs';
import KafkaModel from '@services/model/kafka/kafka';
import MongodbModel from '@services/model/mongodb/mongodb';
import TendbhaModel from '@services/model/mysql/tendbha';
import TendbsingleModel from '@services/model/mysql/tendbsingle';
import PulsarModel from '@services/model/pulsar/pulsar';
import RedisModel from '@services/model/redis/redis';
import RiakModel from '@services/model/riak/riak';
import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
import SqlserverSingleModel from '@services/model/sqlserver/sqlserver-single';
import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

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
  | ClusterTypes.MONGO_SHARED_CLUSTER;

export interface ClusterTypeRelateClusterModel {
  [ClusterTypes.DORIS]: DorisModel;
  [ClusterTypes.ES]: EsModel;
  [ClusterTypes.HDFS]: HdfsModel;
  [ClusterTypes.KAFKA]: KafkaModel;
  [ClusterTypes.MONGO_REPLICA_SET]: MongodbModel;
  [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbModel;
  [ClusterTypes.PULSAR]: PulsarModel;
  [ClusterTypes.REDIS_INSTANCE]: RedisModel;
  [ClusterTypes.REDIS]: RedisModel;
  [ClusterTypes.RIAK]: RiakModel;
  [ClusterTypes.SQLSERVER_HA]: SqlserverHaModel;
  [ClusterTypes.SQLSERVER_SINGLE]: SqlserverSingleModel;
  [ClusterTypes.TENDBCLUSTER]: TendbClusterModel;
  [ClusterTypes.TENDBHA]: TendbhaModel;
  [ClusterTypes.TENDBSINGLE]: TendbsingleModel;
}

export type ClusterModel<T extends keyof ClusterTypeRelateClusterModel> = ClusterTypeRelateClusterModel[T];
