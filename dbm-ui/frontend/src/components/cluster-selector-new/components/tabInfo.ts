import { ClusterTypes } from '@common/const';

import { t } from '@/locales';

import type { ISupportClusterType } from '../types';

export const tabListMap: Record<ISupportClusterType, string> = {
  [ClusterTypes.MONGO_REPLICA_SET]: t('Mongo 副本集'),
  [ClusterTypes.MONGO_SHARED_CLUSTER]: t('Mongo 分片'),
  [ClusterTypes.ORACLE_PRIMARY_STANDBY]: t('Oracle 主从'),
  [ClusterTypes.ORACLE_SINGLE_NONE]: t('Oracle 单节点'),
  [ClusterTypes.REDIS]: t('Redis 集群'),
  [ClusterTypes.REDIS_INSTANCE]: t('Redis 主从'),
  [ClusterTypes.SQLSERVER_HA]: t('SqlServer 主从'),
  [ClusterTypes.SQLSERVER_SINGLE]: t('SqlServer 单节点'),
  [ClusterTypes.TENDBCLUSTER]: 'Tendb Cluster',
  [ClusterTypes.TENDBHA]: t('Mysql 主从'),
  [ClusterTypes.TENDBSINGLE]: t('Mysql 单节点'),
};
