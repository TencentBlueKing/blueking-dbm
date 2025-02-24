/**
 * 机器类型
 */

// mysql
export enum MachineTypes {
  MYSQL_BACKEND = 'backend', // 后端存储
  MYSQL_PROXY = 'proxy', // Proxy
  // SINGLE = 'single',
}
// spider
export enum MachineTypes {
  TENDBCLUSTER_BACKEND = 'backend', // 后端存储
  // SPIDER = 'spider',
  // REMOTE = 'remote',
  TENDBCLUSTER_PROXY = 'proxy', // 接入层Master
}
// redis
export enum MachineTypes {
  REDIS_CLUSTER = 'PredixyRedisCluster', // RedisCluster
  REDIS_INSTANCE = 'RedisInstance', // Redis主从
  REDIS_PROXY = 'proxy',
  REDIS_TENDIS_CACHE = 'TwemproxyRedisInstance', // TendisCache后端存储
  REDIS_TENDIS_PLUS = 'PredixyTendisplusCluster', // TendisPlus后端存储
  REDIS_TENDIS_SSD = 'TwemproxyTendisSSDInstance', // TendisSSD后端存储
}
// mongodb
export enum MachineTypes {
  MONGO_CONFIG = 'mongo_config', // ConfigSvr
  MONGODB = 'mongodb', // 副本集/ShardSvr
  MONGOS = 'mongos', // Mongos
}
// sqlserver
export enum MachineTypes {
  // SQLSERVER_HA = 'sqlserver_ha',
  // SQLSERVER_SINGLE = 'sqlserver_single',
  SQLSERVER = 'sqlserver', // 后端存储
}
// kafka
export enum MachineTypes {
  KAFKA_BROKER = 'broker', // Broker节点
  KAFKA_ZOOKEEPER = 'zookeeper', // Zookeeper节点
}
// es
export enum MachineTypes {
  ES_CLIENT = 'es_client', // Client节点
  ES_DATANODE = 'es_datanode', // 冷/热节点
  ES_MASTER = 'es_master', // Master节点
}
// hdfs
export enum MachineTypes {
  HDFS_DATANODE = 'hdfs_datanode', // DataNode节点
  HDFS_MASTER = 'hdfs_master', // NameNode/Zookeeper/JournalNode节点
}
// pulsar
export enum MachineTypes {
  PULSAR_BOOKKEEPER = 'pulsar_bookkeeper', // Bookkeeper节点
  PULSAR_BROKER = 'pulsar_broker', // Broker节点
  PULSAR_ZOOKEEPER = 'pulsar_zookeeper', // Zookeeper节点
}
// influxdb
export enum MachineTypes {
  INFLUXDB = 'influxdb', // 后端存储
}
// riak
export enum MachineTypes {
  RIAK = 'riak', // 后端存储
}
// doris
export enum MachineTypes {
  DORIS_BACKEND = 'doris_backend', // 冷/热节点
  DORIS_FOLLOWER = 'doris_follower', // Follower节点
  DORIS_OBSERVER = 'doris_observer', // Observer节点
}
