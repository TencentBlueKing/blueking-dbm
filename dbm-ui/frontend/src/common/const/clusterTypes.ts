/**
 * 集群类型
 */
// mysql
export enum ClusterTypes {
  TENDBSINGLE = 'tendbsingle', // MySQL单节点
  TENDBHA = 'tendbha', // MySQL主从
  TENDBCLUSTER = 'tendbcluster',
}
// redis
export enum ClusterTypes {
  REDIS = 'redis', // Redis
  PREDIXY_REDIS_CLUSTER = 'PredixyRedisCluster', // Redis集群
  PREDIXY_TENDISPLUS_CLUSTER = 'PredixyTendisplusCluster', // Tendisplus存储版集群
  TWEMPROXY_REDIS_INSTANCE = 'TwemproxyRedisInstance', // TendisCache集群
  TWEMPROXY_TENDIS_SSD_INSTANCE = 'TwemproxyTendisSSDInstance', // TendisSSD集群
  TWEMPROXY_TENDISPLUS_INSTANCE = 'TwemproxyTendisplusInstance', // Tendis存储版集群
  REDIS_INSTANCE = 'RedisInstance', // RedisCache主从版
  TENDIS_SSD_INSTANCE = 'TendisSSDInstance', // TendisSSD主从版
  TENDIS_PLUS_INSTANCE = 'TendisplusInstance', // Tendisplus主从版
  REDIS_CLUSTER = 'RedisCluster', // RedisCluster集群
  TENDIS_PLUS_CLUSTER = 'TendisplusCluster', // TendisplusCluster集群
  DBMON = 'dbmon', // redis监控
}
// bigdata
export enum ClusterTypes {
  ES = 'es',
  KAFKA = 'kafka',
  HDFS = 'hdfs',
  INFLUXDB = 'influxdb',
  PULSAR = 'pulsar',
  RIAK = 'riak',
  DORIS = 'doris',
}
// mongo
export enum ClusterTypes {
  MONGO_REPLICA_SET = 'MongoReplicaSet', // Mongo副本集群
  MONGO_SHARED_CLUSTER = 'MongoShardedCluster', // Mongo分片集群
  MONGODB = 'mongodb',
}
// sqlserver
export enum ClusterTypes {
  SQLSERVER_SINGLE = 'sqlserver_single', // SQLServer单节点版
  SQLSERVER_HA = 'sqlserver_ha', // SQLServer主从版
}

export type ClusterTypeValues = keyof typeof ClusterTypes;
