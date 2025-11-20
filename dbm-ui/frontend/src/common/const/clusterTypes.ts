/**
 * 集群类型
 */
// mysql
export enum ClusterTypes {
  TENDBHA = 'tendbha', // MySQL主从
  TENDBSINGLE = 'tendbsingle', // MySQL单节点
}
// tendbcluster
export enum ClusterTypes {
  TENDBCLUSTER = 'tendbcluster',
}
// redis
export enum ClusterTypes {
  DBMON = 'dbmon', // redis监控
  PREDIXY_REDIS_CLUSTER = 'PredixyRedisCluster', // RedisCluster集群
  PREDIXY_TENDISPLUS_CLUSTER = 'PredixyTendisplusCluster', // Tendisplus存储版集群
  REDIS = 'redis', // 【Redis集群】
  REDIS_CLUSTER = 'RedisCluster', // RedisCluster集群
  REDIS_INSTANCE = 'RedisInstance', // 【RedisCache主从】
  TENDIS_PLUS_CLUSTER = 'TendisplusCluster', // TendisplusCluster集群
  TENDIS_PLUS_INSTANCE = 'TendisplusInstance', // Tendisplus主从版
  TENDIS_SSD_INSTANCE = 'TendisSSDInstance', // TendisSSD主从版
  TWEMPROXY_REDIS_INSTANCE = 'TwemproxyRedisInstance', // TendisCache集群
  TWEMPROXY_TENDIS_SSD_INSTANCE = 'TwemproxyTendisSSDInstance', // TendisSSD集群
  TWEMPROXY_TENDISPLUS_INSTANCE = 'TwemproxyTendisplusInstance', // Tendis存储版集群
}
// bigdata
export enum ClusterTypes {
  DORIS = 'doris',
  ES = 'es',
  HDFS = 'hdfs',
  INFLUXDB = 'influxdb',
  KAFKA = 'kafka',
  PULSAR = 'pulsar',
  RIAK = 'riak',
}
// mongo
export enum ClusterTypes {
  MONGO_REPLICA_SET = 'MongoReplicaSet', // Mongo副本集群
  MONGO_SHARED_CLUSTER = 'MongoShardedCluster', // Mongo分片集群
  MONGODB = 'mongodb',
}
// sqlserver
export enum ClusterTypes {
  SQLSERVER = 'sqlserver',
  SQLSERVER_HA = 'sqlserver_ha', // SQLServer主从版
  SQLSERVER_SINGLE = 'sqlserver_single', // SQLServer单节点版
}

// oracle
export enum ClusterTypes {
  ORACLE = 'oracle',
  ORACLE_PRIMARY_STANDBY = 'oracle_primary_standby',
  ORACLE_SINGLE_NONE = 'oracle_single_none',
}

export type ClusterTypeValues = keyof typeof ClusterTypes;
