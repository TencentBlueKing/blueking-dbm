import MongodbModel from '@services/model/mongodb/mongodb';
import TendbhaModel from '@services/model/mysql/tendbha';
import OracleHaModel from '@services/model/oracle/oracle-ha';
import OracleSingleModel from '@services/model/oracle/oracle-single';
import RedisModel from '@services/model/redis/redis';
import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
import SqlserverSingleModel from '@services/model/sqlserver/sqlserver-single';
import TendbClustereModel from '@services/model/tendbcluster/tendbcluster';

import { ClusterTypes } from '@common/const';

export type ISupportClusterType =
  | ClusterTypes.MONGO_REPLICA_SET
  | ClusterTypes.MONGO_SHARED_CLUSTER
  | ClusterTypes.REDIS
  | ClusterTypes.REDIS_INSTANCE
  | ClusterTypes.SQLSERVER_HA
  | ClusterTypes.SQLSERVER_SINGLE
  | ClusterTypes.TENDBCLUSTER
  | ClusterTypes.TENDBHA
  | ClusterTypes.TENDBSINGLE
  | ClusterTypes.ORACLE_SINGLE_NONE
  | ClusterTypes.ORACLE_PRIMARY_STANDBY;

export interface ClusterTypeRelateClusterModel {
  [ClusterTypes.MONGO_REPLICA_SET]: MongodbModel;
  [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbModel;
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: OracleHaModel;
  [ClusterTypes.ORACLE_SINGLE_NONE]: OracleSingleModel;
  [ClusterTypes.REDIS_INSTANCE]: RedisModel;
  [ClusterTypes.REDIS]: RedisModel;
  [ClusterTypes.SQLSERVER_HA]: SqlserverHaModel;
  [ClusterTypes.SQLSERVER_SINGLE]: SqlserverSingleModel;
  [ClusterTypes.TENDBCLUSTER]: TendbClustereModel;
  [ClusterTypes.TENDBHA]: TendbhaModel;
  [ClusterTypes.TENDBSINGLE]: TendbhaModel;
}

export type ClusterModel<T extends ISupportClusterType> = ClusterTypeRelateClusterModel[T];
