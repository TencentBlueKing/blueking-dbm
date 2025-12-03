import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
import OracleHaInstanceModel from '@services/model/oracle/oracle-ha-instance';
import RedisInstanceModel from '@services/model/redis/redis-instance';
import SqlserverHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
import TendbClusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';

import { ClusterTypes } from '@common/const';

export type ISupportClusterType =
  | ClusterTypes.TENDBHA
  | ClusterTypes.TENDBCLUSTER
  | ClusterTypes.REDIS_CLUSTER
  | ClusterTypes.REDIS_INSTANCE
  | ClusterTypes.SQLSERVER_HA
  | ClusterTypes.MONGO_REPLICA_SET
  | ClusterTypes.MONGO_SHARED_CLUSTER
  | ClusterTypes.ORACLE_PRIMARY_STANDBY;

export interface ClusterTypeRelateInstanceModel {
  [ClusterTypes.MONGO_REPLICA_SET]: MongodbInstanceModel;
  [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbInstanceModel;
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: OracleHaInstanceModel;
  [ClusterTypes.REDIS_CLUSTER]: RedisInstanceModel;
  [ClusterTypes.REDIS_INSTANCE]: RedisInstanceModel;
  [ClusterTypes.SQLSERVER_HA]: SqlserverHaInstanceModel;
  [ClusterTypes.TENDBCLUSTER]: TendbClusterInstanceModel;
  [ClusterTypes.TENDBHA]: TendbhaInstanceModel;
}

export type InstanceModel<T extends keyof ClusterTypeRelateInstanceModel> = ClusterTypeRelateInstanceModel[T];
