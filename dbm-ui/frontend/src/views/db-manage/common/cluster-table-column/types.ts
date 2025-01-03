import { ClusterTypes } from '@common/const';

import TendbClusterModel from '@/services/model/tendbcluster/tendbcluster';

export type ISupportClusterType = ClusterTypes.TENDBCLUSTER;

interface ClusterTypeRelateClusterModel {
  [ClusterTypes.TENDBCLUSTER]: TendbClusterModel;
}

export type ClusterModel<T extends keyof ClusterTypeRelateClusterModel> = ClusterTypeRelateClusterModel[T];
