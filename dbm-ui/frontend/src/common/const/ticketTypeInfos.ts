import { t } from '@locales/index';

import { ClusterTypes } from './clusterTypes';
import { DBTypes } from './dbTypes';
import { TicketTypes } from './ticketTypes';

/**
 * mysql tickets type info
 */
export const mysqlType = {
  [TicketTypes.MYSQL_SINGLE_APPLY]: {
    id: TicketTypes.MYSQL_SINGLE_APPLY,
    name: t('单节点部署'),
    type: ClusterTypes.TENDBSINGLE,
    dbType: DBTypes.MYSQL,
  },
  [TicketTypes.MYSQL_HA_APPLY]: {
    id: TicketTypes.MYSQL_HA_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.TENDBHA,
    dbType: DBTypes.MYSQL,
  },
  [TicketTypes.TENDBCLUSTER_APPLY]: {
    id: TicketTypes.TENDBCLUSTER_APPLY,
    name: t('TendbCluster分布式集群部署'),
    type: ClusterTypes.TENDBCLUSTER,
    dbType: DBTypes.MYSQL,
  },
};
export type MysqlTypeString = keyof typeof mysqlType;

/**
 * redis tickets type info
 */
export const redisType = {
  [TicketTypes.REDIS_CLUSTER_APPLY]: {
    id: TicketTypes.REDIS_CLUSTER_APPLY,
    name: t('Redis集群部署'),
    type: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    dbType: DBTypes.REDIS,
  },
  [TicketTypes.REDIS_INS_APPLY]: {
    id: TicketTypes.REDIS_INS_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.REDIS_INSTANCE,
    dbType: DBTypes.REDIS,
  },
};

export const bigDataType = {
  [TicketTypes.ES_APPLY]: {
    id: TicketTypes.ES_APPLY,
    name: t('ES集群部署'),
    type: ClusterTypes.ES,
  },
  [TicketTypes.KAFKA_APPLY]: {
    id: TicketTypes.KAFKA_APPLY,
    name: t('Kafka集群部署'),
    type: ClusterTypes.KAFKA,
  },
  [TicketTypes.HDFS_APPLY]: {
    id: TicketTypes.HDFS_APPLY,
    name: t('HDFS集群部署'),
    type: ClusterTypes.HDFS,
  },
  [TicketTypes.PULSAR_APPLY]: {
    id: TicketTypes.PULSAR_APPLY,
    name: t('Pulsar集群部署'),
    type: ClusterTypes.PULSAR,
  },
  [TicketTypes.INFLUXDB_APPLY]: {
    id: TicketTypes.INFLUXDB_APPLY,
    name: t('InfluxDB集群部署'),
    type: ClusterTypes.INFLUXDB,
  },
  [TicketTypes.RIAK_CLUSTER_APPLY]: {
    id: TicketTypes.RIAK_CLUSTER_APPLY,
    name: t('Riak集群部署'),
    type: ClusterTypes.RIAK,
  },
  [TicketTypes.DORIS_APPLY]: {
    id: TicketTypes.DORIS_APPLY,
    name: t('Doris集群部署'),
    type: ClusterTypes.DORIS,
  },
};

export const mongoType = {
  [TicketTypes.MONGODB_SHARD_APPLY]: {
    id: TicketTypes.MONGODB_SHARD_APPLY,
    name: t('MongoDB分片集群部署'),
    type: ClusterTypes.MONGO_SHARED_CLUSTER,
  },
  [TicketTypes.MONGODB_REPLICASET_APPLY]: {
    id: TicketTypes.MONGODB_REPLICASET_APPLY,
    name: t('MongoDB副本集部署'),
    type: ClusterTypes.MONGO_REPLICA_SET,
  },
};

/**
 * sqlserver tickets type info
 */
export const sqlServerType = {
  [TicketTypes.SQLSERVER_SINGLE_APPLY]: {
    id: TicketTypes.SQLSERVER_SINGLE_APPLY,
    name: t('单节点部署'),
    type: ClusterTypes.SQLSERVER_SINGLE,
    dbType: DBTypes.SQLSERVER,
  },
  [TicketTypes.SQLSERVER_HA_APPLY]: {
    id: TicketTypes.SQLSERVER_HA_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.SQLSERVER_HA,
    dbType: DBTypes.SQLSERVER,
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
