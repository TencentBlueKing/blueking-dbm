import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
import RedisInstanceModel from '@services/model/redis/redis-instance';
import SqlserverHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
import SqlserverSingleInstanceModel from '@services/model/sqlserver/sqlserver-single-instance';
import TendbClusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';

import { ClusterTypes } from '@common/const';

export type ISupportClusterType =
  | ClusterTypes.MONGO_REPLICA_SET
  | ClusterTypes.MONGO_SHARED_CLUSTER
  | ClusterTypes.REDIS
  | ClusterTypes.SQLSERVER_HA
  | ClusterTypes.SQLSERVER_SINGLE
  | ClusterTypes.TENDBCLUSTER
  | ClusterTypes.TENDBHA
  | ClusterTypes.TENDBSINGLE;

export interface ClusterTypeRelateInstanceModel {
  [ClusterTypes.MONGO_REPLICA_SET]: MongodbInstanceModel;
  [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbInstanceModel;
  [ClusterTypes.REDIS]: RedisInstanceModel;
  [ClusterTypes.SQLSERVER_HA]: SqlserverHaInstanceModel;
  [ClusterTypes.SQLSERVER_SINGLE]: SqlserverSingleInstanceModel;
  [ClusterTypes.TENDBCLUSTER]: TendbClusterInstanceModel;
  [ClusterTypes.TENDBHA]: TendbhaInstanceModel;
  [ClusterTypes.TENDBSINGLE]: TendbhaInstanceModel;
}

export type InstanceModel<T extends ISupportClusterType> = ClusterTypeRelateInstanceModel[T];
