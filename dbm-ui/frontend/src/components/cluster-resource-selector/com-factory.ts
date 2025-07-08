import { ClusterTypes, DBTypes } from '@common/const';

import { t } from '@locales/index';

export default {
  // redis 集群
  [ClusterTypes.REDIS]: {
    // 过滤参数
    cluster_type: [
      ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
      ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
      ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      ClusterTypes.PREDIXY_REDIS_CLUSTER,
    ].join(','),
    db_type: DBTypes.REDIS,
    id: ClusterTypes.REDIS,
    name: t('Redis 集群'),
  },
  // redis 主从集群
  [ClusterTypes.REDIS_INSTANCE]: {
    cluster_type: ClusterTypes.REDIS_INSTANCE,
    db_type: DBTypes.REDIS,
    id: ClusterTypes.REDIS_INSTANCE,
    name: t('Redis 主从'),
  },
  [ClusterTypes.TENDBCLUSTER]: {
    cluster_type: ClusterTypes.TENDBCLUSTER,
    db_type: DBTypes.TENDBCLUSTER,
    id: ClusterTypes.TENDBCLUSTER,
    name: 'TenDBCluster',
  },
  [ClusterTypes.TENDBHA]: {
    cluster_type: ClusterTypes.TENDBHA,
    db_type: DBTypes.MYSQL,
    id: ClusterTypes.TENDBHA,
    name: t('MySQL 主从'),
  },
  [ClusterTypes.TENDBSINGLE]: {
    cluster_type: ClusterTypes.TENDBSINGLE,
    db_type: DBTypes.MYSQL,
    id: ClusterTypes.TENDBSINGLE,
    name: t('MySQL 单节点'),
  },
};
