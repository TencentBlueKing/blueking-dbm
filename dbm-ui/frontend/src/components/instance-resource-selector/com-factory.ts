import { ClusterTypes, DBTypes, queryClusterTypes } from '@common/const';

export default {
  [ClusterTypes.REDIS]: {
    cluster_type: queryClusterTypes[DBTypes.REDIS].join(','),
    db_type: DBTypes.REDIS,
  },
  [ClusterTypes.TENDBCLUSTER]: {
    cluster_type: ClusterTypes.TENDBCLUSTER,
    db_type: DBTypes.TENDBCLUSTER,
  },
  [ClusterTypes.TENDBHA]: {
    cluster_type: ClusterTypes.TENDBHA,
    db_type: DBTypes.MYSQL,
  },
  [ClusterTypes.TENDBSINGLE]: {
    cluster_type: ClusterTypes.TENDBSINGLE,
    db_type: DBTypes.MYSQL,
  },
};
