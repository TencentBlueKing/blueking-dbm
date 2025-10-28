import { ClusterTypes } from './clusterTypes';

export const clusterTypeListPageMap: Record<string, string> = {
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: 'redisClusterDetail',
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: 'redisClusterDetail',
  // redis
  [ClusterTypes.REDIS_INSTANCE]: 'redisClusterHaDetail',
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: 'redisClusterDetail',
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: 'redisClusterDetail',
};
