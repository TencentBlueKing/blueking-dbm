import { ClusterTypes } from './clusterTypes';

export const clusterTypeListPageMap: Record<string, string> = {
  // redis
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: 'redisClusterDetail',
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: 'redisClusterDetail',
  [ClusterTypes.REDIS_INSTANCE]: 'redisClusterHaDetail',
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: 'redisClusterDetail',
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: 'redisClusterDetail',
};
