import MongodbMachineModel from '@services/model/mongodb/mongodb-machine';
import TendbhaMachineModel from '@services/model/mysql/tendbha-machine';
import TendbSingleMachineModel from '@services/model/mysql/tendbSingle-machine';
import RedisMachineModel from '@services/model/redis/redis-machine';
import SqlserverMachineModel from '@services/model/sqlserver/sqlserver-machine';
import TendbClusterMachineModel from '@services/model/tendbcluster/tendbcluster-machine';

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

export interface ClusterTypeRelateMachineModel {
  [ClusterTypes.MONGO_REPLICA_SET]: MongodbMachineModel;
  [ClusterTypes.MONGO_SHARED_CLUSTER]: MongodbMachineModel;
  [ClusterTypes.REDIS]: RedisMachineModel;
  [ClusterTypes.SQLSERVER_HA]: SqlserverMachineModel;
  [ClusterTypes.SQLSERVER_SINGLE]: SqlserverMachineModel;
  [ClusterTypes.TENDBCLUSTER]: TendbClusterMachineModel;
  [ClusterTypes.TENDBHA]: TendbhaMachineModel;
  [ClusterTypes.TENDBSINGLE]: TendbSingleMachineModel;
}

export type MachineModel<T extends ISupportClusterType> = ClusterTypeRelateMachineModel[T];
