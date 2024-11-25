/**
 * 机器类型
 */

export enum MachineTypes {
  // mysql
  BACKEND = 'backend',
  PROXY = 'proxy',
  SINGLE = 'single',

  // spider
  SPIDER = 'spider',
  REMOTE = 'remote',

  // redis
  TENDISCACHE = 'tendiscache',
  TENDISSSD = 'tendisssd',
  TENDISPLUS = 'tendisplus',
  TWEMPROXY = 'twemproxy',
  PREDIXY = 'predixy',

  // mongodb
  MONGOS = 'mongos',
  MONGODB = 'mongodb',
  MONGO_CONFIG = 'mongo_config',

  // sqlserver
  SQLSERVER_HA = 'sqlserver_ha',
  SQLSERVER_SINGLE = 'sqlserver_single',

  // kafka
  BROKER = 'broker',
  ZOOKEEPER = 'zookeeper',

  // es
  ES_DATANODE = 'es_datanode',
  ES_MASTER = 'es_master',
  ES_CLIENT = 'es_client',

  // hdfs
  HDFS_MASTER = 'hdfs_master',
  HDFS_DATANODE = 'hdfs_datanode',

  // pulsar
  PULSAR_BROKER = 'pulsar_broker',
  PULSAR_BOOKKEEPER = 'pulsar_bookkeeper',
  PULSAR_ZOOKEEPER = 'pulsar_zookeeper',

  // doris
  DORIS_FOLLOWER = 'doris_follower',
  DORIS_OBSERVER = 'doris_observer',
  DORIS_BACKEND = 'doris_backend',

  // influxdb
  INFLUXDB = 'influxdb',

  // riak
  RIAK = 'riak',
}
