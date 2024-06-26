import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

import { ClusterTypes } from './clusterTypes';
import { DBTypes } from './dbTypes';

interface InfoItem {
  id: ClusterTypes;
  name: string;
  dbType: DBTypes;
  moduleId?: ExtractedControllerDataKeys;
}
type InfoType = {
  [x in ClusterTypes]?: InfoItem;
};
type RequiredInfoType = {
  [x in ClusterTypes]: InfoItem;
};

const mysql: InfoType = {
  [ClusterTypes.TENDBSINGLE]: {
    id: ClusterTypes.TENDBSINGLE,
    name: t('MySQL单节点'),
    dbType: DBTypes.MYSQL,
  },
  [ClusterTypes.TENDBHA]: {
    id: ClusterTypes.TENDBHA,
    name: t('MySQL主从'),
    dbType: DBTypes.MYSQL,
  },
  [ClusterTypes.TENDBCLUSTER]: {
    id: ClusterTypes.TENDBCLUSTER,
    name: 'TenDBCluster',
    dbType: DBTypes.MYSQL,
  },
};

const redis: InfoType = {
  [ClusterTypes.REDIS]: {
    id: ClusterTypes.REDIS,
    name: 'Redis',
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
    id: ClusterTypes.PREDIXY_REDIS_CLUSTER,
    name: t('Redis集群'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
    id: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    name: t('Tendisplus存储版集群'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
    id: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    name: t('TendisCache集群'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
    id: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    name: t('TendisSSD集群'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.TWEMPROXY_TENDISPLUS_INSTANCE]: {
    id: ClusterTypes.TWEMPROXY_TENDISPLUS_INSTANCE,
    name: t('Tendis存储版集群'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.REDIS_INSTANCE]: {
    id: ClusterTypes.REDIS_INSTANCE,
    name: t('RedisCache主从版'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.TENDIS_SSD_INSTANCE]: {
    id: ClusterTypes.TENDIS_SSD_INSTANCE,
    name: t('TendisSSD主从版'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.TENDIS_PLUS_INSTANCE]: {
    id: ClusterTypes.TENDIS_PLUS_INSTANCE,
    name: t('Tendisplus主从版'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.REDIS_CLUSTER]: {
    id: ClusterTypes.REDIS_CLUSTER,
    name: t('RedisCluster集群'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.TENDIS_PLUS_CLUSTER]: {
    id: ClusterTypes.TENDIS_PLUS_CLUSTER,
    name: t('TendisplusCluster集群'),
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.DBMON]: {
    id: ClusterTypes.DBMON,
    name: t('Redis监控'),
    dbType: DBTypes.REDIS,
  },
};

const bigdata: InfoType = {
  [ClusterTypes.ES]: {
    id: ClusterTypes.ES,
    name: 'ES',
    dbType: DBTypes.ES,
    moduleId: 'bigdata',
  },
  [ClusterTypes.KAFKA]: {
    id: ClusterTypes.KAFKA,
    name: 'Kafka',
    dbType: DBTypes.KAFKA,
    moduleId: 'bigdata',
  },
  [ClusterTypes.HDFS]: {
    id: ClusterTypes.HDFS,
    name: 'HDFS',
    dbType: DBTypes.HDFS,
    moduleId: 'bigdata',
  },
  [ClusterTypes.INFLUXDB]: {
    id: ClusterTypes.INFLUXDB,
    name: 'InfuxDB',
    dbType: DBTypes.INFLUXDB,
    moduleId: 'bigdata',
  },
  [ClusterTypes.PULSAR]: {
    id: ClusterTypes.PULSAR,
    name: 'Pulsar',
    dbType: DBTypes.PULSAR,
    moduleId: 'bigdata',
  },
  [ClusterTypes.RIAK]: {
    id: ClusterTypes.RIAK,
    name: 'Riak',
    dbType: DBTypes.RIAK,
    moduleId: 'bigdata',
  },
  [ClusterTypes.DORIS]: {
    id: ClusterTypes.DORIS,
    name: 'Dodis',
    dbType: DBTypes.DORIS,
    moduleId: 'bigdata',
  },
};

const mongo: InfoType = {
  [ClusterTypes.MONGO_REPLICA_SET]: {
    id: ClusterTypes.MONGO_REPLICA_SET,
    name: t('Mongo副本集群'),
    dbType: DBTypes.MONGODB,
  },
  [ClusterTypes.MONGO_SHARED_CLUSTER]: {
    id: ClusterTypes.MONGO_SHARED_CLUSTER,
    name: t('Mongo分片集群'),
    dbType: DBTypes.MONGODB,
  },
};

const sqlserver: InfoType = {
  [ClusterTypes.SQLSERVER_SINGLE]: {
    id: ClusterTypes.SQLSERVER_SINGLE,
    name: t('SQLServer单节点版'),
    dbType: DBTypes.SQLSERVER,
  },
  [ClusterTypes.SQLSERVER_HA]: {
    id: ClusterTypes.SQLSERVER_HA,
    name: t('SQLServer主从版'),
    dbType: DBTypes.SQLSERVER,
  },
};

/**
 * 集群类型对应配置
 */
export const clusterTypeInfos: RequiredInfoType = {
  ...mysql,
  ...redis,
  ...bigdata,
  ...mongo,
  ...sqlserver,
} as RequiredInfoType;
export type ClusterTypeInfos = keyof typeof clusterTypeInfos;
