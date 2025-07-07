import { ClusterTypes, DBTypes } from '@common/const';

import { t } from '@locales/index';

export default {
  [ClusterTypes.REDIS]: {
    id: ClusterTypes.REDIS,
    name: 'Redis',
    params: {
      db_type: DBTypes.REDIS,
    },
  },
  [ClusterTypes.TENDBCLUSTER]: {
    id: ClusterTypes.TENDBCLUSTER,
    name: 'Tendb Cluster',
    params: {
      cluster_type: ClusterTypes.TENDBCLUSTER,
      db_type: DBTypes.TENDBCLUSTER,
    },
  },
  [ClusterTypes.TENDBHA]: {
    id: ClusterTypes.TENDBHA,
    name: t('MySQL 主从'),
    params: {
      cluster_type: ClusterTypes.TENDBHA,
      db_type: DBTypes.MYSQL,
    },
  },
  [ClusterTypes.TENDBSINGLE]: {
    id: ClusterTypes.TENDBSINGLE,
    name: t('MySQL 单节点'),
    params: {
      cluster_type: ClusterTypes.TENDBSINGLE,
      db_type: DBTypes.MYSQL,
    },
  },
};
