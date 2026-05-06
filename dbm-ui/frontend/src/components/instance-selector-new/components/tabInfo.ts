import { ClusterTypes } from '@common/const';

import { t } from '@/locales';

import type { ISupportClusterType } from '../types';

export const tabListMap: Record<ISupportClusterType, string> = {
  [ClusterTypes.MONGO_REPLICA_SET]: t('Mongo 副本集'),
  [ClusterTypes.MONGO_SHARED_CLUSTER]: t('Mongo 分片'),
  [ClusterTypes.REDIS]: 'Redis',
  [ClusterTypes.SQLSERVER_HA]: t('SqlServer 主从'),
  [ClusterTypes.SQLSERVER_SINGLE]: t('SqlServer 单节点'),
  [ClusterTypes.TENDBCLUSTER]: 'Tendb Cluster',
  [ClusterTypes.TENDBHA]: t('Mysql 主从'),
  [ClusterTypes.TENDBSINGLE]: t('Mysql 单节点'),
};
