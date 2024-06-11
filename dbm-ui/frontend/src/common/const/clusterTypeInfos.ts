import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

import { ClusterTypes } from './clusterTypes';
import { DBTypes } from './dbTypes';

interface InfoItem {
  id: ClusterTypes;
  name: string;
  dbType: DBTypes;
  moduleId: ExtractedControllerDataKeys;
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
    moduleId: 'mysql',
  },
  [ClusterTypes.TENDBHA]: {
    id: ClusterTypes.TENDBHA,
    name: t('MySQL主从'),
    dbType: DBTypes.MYSQL,
    moduleId: 'mysql',
  },
  [ClusterTypes.TENDBCLUSTER]: {
    id: ClusterTypes.TENDBCLUSTER,
    name: 'TenDBCluster',
    dbType: DBTypes.MYSQL,
    moduleId: 'mysql',
  },
};

const redis: InfoType = {
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
    id: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    name: 'TendisCache',
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
  },
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
    id: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    name: 'TendisSSD',
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
  },
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
    id: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    name: 'Tendisplus',
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
  },
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
    id: ClusterTypes.PREDIXY_REDIS_CLUSTER,
    name: 'RedisCluster',
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
  },
  [ClusterTypes.REDIS_INSTANCE]: {
    id: ClusterTypes.REDIS_INSTANCE,
    name: t('Redis主从'),
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
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
    name: 'Doris',
    dbType: DBTypes.DORIS,
    moduleId: 'bigdata',
  },
};

const mongo: InfoType = {
  [ClusterTypes.MONGO_REPLICA_SET]: {
    id: ClusterTypes.MONGO_REPLICA_SET,
    name: t('Mongo副本集'),
    dbType: DBTypes.MONGODB,
    moduleId: 'mongodb',
  },
  [ClusterTypes.MONGO_SHARED_CLUSTER]: {
    id: ClusterTypes.MONGO_SHARED_CLUSTER,
    name: t('Mongo分片集'),
    dbType: DBTypes.MONGODB,
    moduleId: 'mongodb',
  },
};

const sqlserver: InfoType = {
  [ClusterTypes.SQLSERVER_SINGLE]: {
    id: ClusterTypes.SQLSERVER_SINGLE,
    name: t('SQLServer单节点'),
    dbType: DBTypes.SQLSERVER,
    moduleId: 'sqlserver',
  },
  [ClusterTypes.SQLSERVER_HA]: {
    id: ClusterTypes.SQLSERVER_HA,
    name: t('SQLServer主从'),
    dbType: DBTypes.SQLSERVER,
    moduleId: 'sqlserver',
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
