/**
 * 机器类型
 */

// mysql
export enum MachineTypes {
  BACKEND = 'backend',
  PROXY = 'proxy',
  SINGLE = 'single',
}
// spider
export enum MachineTypes {
  SPIDER = 'spider',
  REMOTE = 'remote',
}
// redis
export enum MachineTypes {
  TENDISCACHE = 'tendiscache',
  TENDISSSD = 'tendisssd',
  TENDISPLUS = 'tendisplus',
  TWEMPROXY = 'twemproxy',
  PREDIXY = 'predixy',
}
// mongodb
export enum MachineTypes {
  MONGOS = 'mongos',
  MONGODB = 'mongodb',
  MONGO_CONFIG = 'mongo_config',
}
// sqlserver
export enum MachineTypes {
  SQLSERVER_HA = 'sqlserver_ha',
  SQLSERVER_SINGLE = 'sqlserver_single',
}
// kefka
export enum MachineTypes {
  BROKER = 'broker',
  ZOOKEEPER = 'zookeeper',
}
// es
export enum MachineTypes {
  ES_DATANODE = 'es_datanode',
  ES_MASTER = 'es_master',
  ES_CLIENT = 'es_client',
}
// hdfs
export enum MachineTypes {
  HDFS_MASTER = 'hdfs_master',
  HDFS_DATANODE = 'hdfs_datanode',
}
// pulsar
export enum MachineTypes {
  PULSAR_BROKER = 'pulsar_broker',
  PULSAR_BOOKKEEPER = 'pulsar_bookkeeper',
  PULSAR_ZOOKEEPER = 'pulsar_zookeeper',
}
// influxdb
export enum MachineTypes {
  INFLUXDB = 'influxdb',
}
// riak
export enum MachineTypes {
  RIAK = 'riak',
}
