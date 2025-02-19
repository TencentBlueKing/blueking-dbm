import { t } from '@locales/index';

import { ClusterTypes } from './clusterTypes';
import { DBTypes } from './dbTypes';
import { TicketTypes } from './ticketTypes';

/**
 * mysql tickets type info
 */
export const mysqlType = {
  [TicketTypes.MYSQL_HA_APPLY]: {
    dbType: DBTypes.MYSQL,
    id: TicketTypes.MYSQL_HA_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.TENDBHA,
  },
  [TicketTypes.MYSQL_SINGLE_APPLY]: {
    dbType: DBTypes.MYSQL,
    id: TicketTypes.MYSQL_SINGLE_APPLY,
    name: t('单节点部署'),
    type: ClusterTypes.TENDBSINGLE,
  },
  [TicketTypes.TENDBCLUSTER_APPLY]: {
    dbType: DBTypes.MYSQL,
    id: TicketTypes.TENDBCLUSTER_APPLY,
    name: t('TendbCluster分布式集群部署'),
    type: ClusterTypes.TENDBCLUSTER,
  },
};
export type MysqlTypeString = keyof typeof mysqlType;

/**
 * redis tickets type info
 */
export const redisType = {
  [TicketTypes.REDIS_CLUSTER_APPLY]: {
    dbType: DBTypes.REDIS,
    id: TicketTypes.REDIS_CLUSTER_APPLY,
    name: t('Redis集群部署'),
    type: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
  },
  [TicketTypes.REDIS_INS_APPLY]: {
    dbType: DBTypes.REDIS,
    id: TicketTypes.REDIS_INS_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.REDIS_INSTANCE,
  },
};

export const bigDataType = {
  [TicketTypes.DORIS_APPLY]: {
    id: TicketTypes.DORIS_APPLY,
    name: t('Doris集群部署'),
    type: ClusterTypes.DORIS,
  },
  [TicketTypes.ES_APPLY]: {
    id: TicketTypes.ES_APPLY,
    name: t('ES集群部署'),
    type: ClusterTypes.ES,
  },
  [TicketTypes.HDFS_APPLY]: {
    id: TicketTypes.HDFS_APPLY,
    name: t('HDFS集群部署'),
    type: ClusterTypes.HDFS,
  },
  [TicketTypes.INFLUXDB_APPLY]: {
    id: TicketTypes.INFLUXDB_APPLY,
    name: t('InfluxDB集群部署'),
    type: ClusterTypes.INFLUXDB,
  },
  [TicketTypes.KAFKA_APPLY]: {
    id: TicketTypes.KAFKA_APPLY,
    name: t('Kafka集群部署'),
    type: ClusterTypes.KAFKA,
  },
  [TicketTypes.PULSAR_APPLY]: {
    id: TicketTypes.PULSAR_APPLY,
    name: t('Pulsar集群部署'),
    type: ClusterTypes.PULSAR,
  },
  [TicketTypes.RIAK_CLUSTER_APPLY]: {
    id: TicketTypes.RIAK_CLUSTER_APPLY,
    name: t('Riak集群部署'),
    type: ClusterTypes.RIAK,
  },
};

export const mongoType = {
  [TicketTypes.MONGODB_REPLICASET_APPLY]: {
    id: TicketTypes.MONGODB_REPLICASET_APPLY,
    name: t('MongoDB副本集部署'),
    type: ClusterTypes.MONGO_REPLICA_SET,
  },
  [TicketTypes.MONGODB_SHARD_APPLY]: {
    id: TicketTypes.MONGODB_SHARD_APPLY,
    name: t('MongoDB分片集群部署'),
    type: ClusterTypes.MONGO_SHARED_CLUSTER,
  },
};

/**
 * sqlserver tickets type info
 */
export const sqlServerType = {
  [TicketTypes.SQLSERVER_HA_APPLY]: {
    dbType: DBTypes.SQLSERVER,
    id: TicketTypes.SQLSERVER_HA_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.SQLSERVER_HA,
  },
  [TicketTypes.SQLSERVER_SINGLE_APPLY]: {
    dbType: DBTypes.SQLSERVER,
    id: TicketTypes.SQLSERVER_SINGLE_APPLY,
    name: t('单节点部署'),
    type: ClusterTypes.SQLSERVER_SINGLE,
  },
};

export type SqlServerTypeString = keyof typeof sqlServerType;

/** all service tickets */
export const serviceTicketTypes = {
  ...mysqlType,
  ...redisType,
  ...bigDataType,
  ...mongoType,
  ...sqlServerType,
};
export type ServiceTicketTypeStrings = keyof typeof serviceTicketTypes;
