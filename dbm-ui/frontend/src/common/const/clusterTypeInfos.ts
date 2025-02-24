import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

import { ClusterTypes } from './clusterTypes';
import { DBTypes } from './dbTypes';
import { MachineTypes } from './machineTypes';

export interface ClusterTypeInfoItem {
  dbType: DBTypes;
  id: ClusterTypes;
  machineList: {
    id: MachineTypes;
    name: string;
  }[];
  moduleId: ExtractedControllerDataKeys;
  name: string;
  specClusterName: string; // 规格对应的集群名，磨平集群类型差异
}
type InfoType = {
  [x in ClusterTypes]?: ClusterTypeInfoItem;
};
type RequiredInfoType = {
  [x in ClusterTypes]: ClusterTypeInfoItem;
};

const mysql: InfoType = {
  [ClusterTypes.TENDBHA]: {
    dbType: DBTypes.MYSQL,
    id: ClusterTypes.TENDBHA,
    machineList: [
      {
        id: MachineTypes.MYSQL_PROXY,
        name: 'Proxy',
      },
      {
        id: MachineTypes.MYSQL_BACKEND,
        name: t('后端存储'),
      },
    ],
    moduleId: 'mysql',
    name: t('MySQL主从'),
    specClusterName: 'MySQL',
  },
  [ClusterTypes.TENDBSINGLE]: {
    dbType: DBTypes.MYSQL,
    id: ClusterTypes.TENDBSINGLE,
    machineList: [
      {
        id: MachineTypes.MYSQL_PROXY,
        name: 'Proxy',
      },
      {
        id: MachineTypes.MYSQL_BACKEND,
        name: t('后端存储'),
      },
    ],
    moduleId: 'mysql',
    name: t('MySQL单节点'),
    specClusterName: 'MySQL',
  },
};

const spider: InfoType = {
  [ClusterTypes.TENDBCLUSTER]: {
    dbType: DBTypes.TENDBCLUSTER,
    id: ClusterTypes.TENDBCLUSTER,
    machineList: [
      {
        id: MachineTypes.TENDBCLUSTER_PROXY,
        name: t('接入层Master'),
      },
      {
        id: MachineTypes.TENDBCLUSTER_BACKEND,
        name: t('后端存储'),
      },
    ],
    moduleId: 'mysql',
    name: 'TenDBCluster',
    specClusterName: 'TenDBCluster',
  },
};

const redis: InfoType = {
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.PREDIXY_REDIS_CLUSTER,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_CACHE,
        name: t('TendisCache/RedisCluster/Redis主从 后端存储'),
      },
      {
        id: MachineTypes.REDIS_PROXY,
        name: 'Proxy',
      },
    ],
    moduleId: 'redis',
    name: 'RedisCluster',
    specClusterName: 'Redis',
  },
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_PLUS,
        name: t('TendisPlus后端存储'),
      },
      {
        id: MachineTypes.REDIS_PROXY,
        name: 'Proxy',
      },
    ],
    moduleId: 'redis',
    name: 'Tendisplus',
    specClusterName: 'Redis',
  },
  [ClusterTypes.REDIS_INSTANCE]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.REDIS_INSTANCE,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_CACHE,
        name: t('TendisCache/RedisCluster/Redis主从 后端存储'),
      },
    ],
    moduleId: 'redis',
    name: t('Redis主从'),
    specClusterName: 'Redis',
  },
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_CACHE,
        name: t('TendisCache/RedisCluster/Redis主从 后端存储'),
      },
      {
        id: MachineTypes.REDIS_PROXY,
        name: 'Proxy',
      },
    ],
    moduleId: 'redis',
    name: 'TendisCache',
    specClusterName: 'Redis',
  },
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_CACHE,
        name: t('TendisCache/RedisCluster/Redis主从 后端存储'),
      },
      {
        id: MachineTypes.REDIS_PROXY,
        name: 'Proxy',
      },
    ],
    moduleId: 'redis',
    name: 'TendisSSD',
    specClusterName: 'Redis',
  },
};

const bigdata: InfoType = {
  [ClusterTypes.DORIS]: {
    dbType: DBTypes.DORIS,
    id: ClusterTypes.DORIS,
    machineList: [
      {
        id: MachineTypes.DORIS_FOLLOWER,
        name: t('Follower节点规格'),
      },
      {
        id: MachineTypes.DORIS_OBSERVER,
        name: t('Observer节点规格'),
      },
      {
        id: MachineTypes.DORIS_BACKEND,
        name: t('冷_热节点规格'),
      },
    ],
    moduleId: 'bigdata',
    name: 'Doris',
    specClusterName: 'Doris',
  },
  [ClusterTypes.ES]: {
    dbType: DBTypes.ES,
    id: ClusterTypes.ES,
    machineList: [
      {
        id: MachineTypes.ES_MASTER,
        name: t('Master节点'),
      },
      {
        id: MachineTypes.ES_CLIENT,
        name: t('Client节点'),
      },
      {
        id: MachineTypes.ES_DATANODE,
        name: t('冷_热节点'),
      },
    ],
    moduleId: 'bigdata',
    name: 'ElasticSearch',
    specClusterName: 'ElasticSearch',
  },
  [ClusterTypes.HDFS]: {
    dbType: DBTypes.HDFS,
    id: ClusterTypes.HDFS,
    machineList: [
      {
        id: MachineTypes.HDFS_DATANODE,
        name: t('DataNode节点'),
      },
      {
        id: MachineTypes.HDFS_MASTER,
        name: t('NameNode_Zookeeper_JournalNode节点'),
      },
    ],
    moduleId: 'bigdata',
    name: 'HDFS',
    specClusterName: 'HDFS',
  },
  [ClusterTypes.INFLUXDB]: {
    dbType: DBTypes.INFLUXDB,
    id: ClusterTypes.INFLUXDB,
    machineList: [
      {
        id: MachineTypes.INFLUXDB,
        name: t('后端存储机型'),
      },
    ],
    moduleId: 'bigdata',
    name: 'InfuxDB',
    specClusterName: 'InfuxDB',
  },
  [ClusterTypes.KAFKA]: {
    dbType: DBTypes.KAFKA,
    id: ClusterTypes.KAFKA,
    machineList: [
      {
        id: MachineTypes.KAFKA_ZOOKEEPER,
        name: t('Zookeeper节点'),
      },
      {
        id: MachineTypes.KAFKA_BROKER,
        name: t('Broker节点'),
      },
    ],
    moduleId: 'bigdata',
    name: 'Kafka',
    specClusterName: 'Kafka',
  },
  [ClusterTypes.PULSAR]: {
    dbType: DBTypes.PULSAR,
    id: ClusterTypes.PULSAR,
    machineList: [
      {
        id: MachineTypes.PULSAR_BOOKKEEPER,
        name: t('Bookkeeper节点'),
      },
      {
        id: MachineTypes.PULSAR_ZOOKEEPER,
        name: t('Zookeeper节点'),
      },
      {
        id: MachineTypes.PULSAR_BROKER,
        name: t('Broker节点'),
      },
    ],
    moduleId: 'bigdata',
    name: 'Pulsar',
    specClusterName: 'Pulsar',
  },
  [ClusterTypes.RIAK]: {
    dbType: DBTypes.RIAK,
    id: ClusterTypes.RIAK,
    machineList: [
      {
        id: MachineTypes.RIAK,
        name: t('后端存储'),
      },
    ],
    moduleId: 'bigdata',
    name: 'Riak',
    specClusterName: 'Riak',
  },
};

const mongodb: InfoType = {
  [ClusterTypes.MONGO_REPLICA_SET]: {
    dbType: DBTypes.MONGODB,
    id: ClusterTypes.MONGO_REPLICA_SET,
    machineList: [
      {
        id: MachineTypes.MONGODB,
        name: '副本集/ShardSvr',
      },
    ],
    moduleId: 'mongodb',
    name: t('Mongo副本集'),
    specClusterName: 'MongoDB',
  },
  [ClusterTypes.MONGO_SHARED_CLUSTER]: {
    dbType: DBTypes.MONGODB,
    id: ClusterTypes.MONGO_SHARED_CLUSTER,
    machineList: [
      {
        id: MachineTypes.MONGOS,
        name: 'Mongos',
      },
      {
        id: MachineTypes.MONGODB,
        name: t('副本集/ShardSvr'),
      },
      {
        id: MachineTypes.MONGO_CONFIG,
        name: 'ConfigSvr',
      },
    ],
    moduleId: 'mongodb',
    name: t('Mongo分片集群'),
    specClusterName: 'MongoDB',
  },
};

const sqlserver: InfoType = {
  [ClusterTypes.SQLSERVER_HA]: {
    dbType: DBTypes.SQLSERVER,
    id: ClusterTypes.SQLSERVER_HA,
    machineList: [
      {
        id: MachineTypes.SQLSERVER,
        name: t('后端存储'),
      },
    ],
    moduleId: 'sqlserver',
    name: t('SQLServer主从'),
    specClusterName: 'SQLServer',
  },
  [ClusterTypes.SQLSERVER_SINGLE]: {
    dbType: DBTypes.SQLSERVER,
    id: ClusterTypes.SQLSERVER_SINGLE,
    machineList: [
      {
        id: MachineTypes.SQLSERVER,
        name: t('后端存储'),
      },
    ],
    moduleId: 'sqlserver',
    name: t('SQLServer单节点'),
    specClusterName: 'SQLServer',
  },
};

/**
 * 集群类型对应配置
 */
export const clusterTypeInfos: RequiredInfoType = {
  ...mysql,
  ...spider,
  ...redis,
  ...bigdata,
  ...mongodb,
  ...sqlserver,
} as RequiredInfoType;
export type ClusterTypeInfos = keyof typeof clusterTypeInfos;
