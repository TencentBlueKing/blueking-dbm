import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

import { ClusterTypes } from './clusterTypes';
import { DBTypes } from './dbTypes';
import { MachineTypes } from './machineTypes';

export interface ClusterTypeInfoItem {
  id: ClusterTypes;
  name: string;
  specClusterName: string; // 规格对应的集群名，磨平集群类型差异
  dbType: DBTypes;
  moduleId: ExtractedControllerDataKeys;
  machineList: {
    id: MachineTypes;
    name: string;
  }[];
}
type InfoType = {
  [x in ClusterTypes]?: ClusterTypeInfoItem;
};
type RequiredInfoType = {
  [x in ClusterTypes]: ClusterTypeInfoItem;
};

const mysql: InfoType = {
  [ClusterTypes.TENDBSINGLE]: {
    id: ClusterTypes.TENDBSINGLE,
    name: t('MySQL单节点'),
    specClusterName: 'MySQL',
    dbType: DBTypes.MYSQL,
    moduleId: 'mysql',
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
  },
  [ClusterTypes.TENDBHA]: {
    id: ClusterTypes.TENDBHA,
    name: t('MySQL主从'),
    specClusterName: 'MySQL',
    dbType: DBTypes.MYSQL,
    moduleId: 'mysql',
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
  },
};

const spider: InfoType = {
  [ClusterTypes.TENDBCLUSTER]: {
    id: ClusterTypes.TENDBCLUSTER,
    name: 'TenDBCluster',
    specClusterName: 'TenDBCluster',
    dbType: DBTypes.TENDBCLUSTER,
    moduleId: 'mysql',
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
  },
};

const redis: InfoType = {
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
    id: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    name: 'TendisCache',
    specClusterName: 'Redis',
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
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
  },
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
    id: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    name: 'TendisSSD',
    specClusterName: 'Redis',
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
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
  },
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
    id: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    name: 'Tendisplus',
    specClusterName: 'Redis',
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
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
  },
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
    id: ClusterTypes.PREDIXY_REDIS_CLUSTER,
    name: 'RedisCluster',
    specClusterName: 'Redis',
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
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
  },
  [ClusterTypes.REDIS_INSTANCE]: {
    id: ClusterTypes.REDIS_INSTANCE,
    name: t('Redis主从'),
    specClusterName: 'Redis',
    dbType: DBTypes.REDIS,
    moduleId: 'redis',
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_CACHE,
        name: t('TendisCache/RedisCluster/Redis主从 后端存储'),
      },
    ],
  },
};

const bigdata: InfoType = {
  [ClusterTypes.ES]: {
    id: ClusterTypes.ES,
    name: 'ElasticSearch',
    specClusterName: 'ElasticSearch',
    dbType: DBTypes.ES,
    moduleId: 'bigdata',
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
  },
  [ClusterTypes.KAFKA]: {
    id: ClusterTypes.KAFKA,
    name: 'Kafka',
    specClusterName: 'Kafka',
    dbType: DBTypes.KAFKA,
    moduleId: 'bigdata',
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
  },
  [ClusterTypes.HDFS]: {
    id: ClusterTypes.HDFS,
    name: 'HDFS',
    specClusterName: 'HDFS',
    dbType: DBTypes.HDFS,
    moduleId: 'bigdata',
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
  },
  [ClusterTypes.INFLUXDB]: {
    id: ClusterTypes.INFLUXDB,
    name: 'InfuxDB',
    specClusterName: 'InfuxDB',
    dbType: DBTypes.INFLUXDB,
    moduleId: 'bigdata',
    machineList: [
      {
        id: MachineTypes.INFLUXDB,
        name: t('后端存储机型'),
      },
    ],
  },
  [ClusterTypes.PULSAR]: {
    id: ClusterTypes.PULSAR,
    name: 'Pulsar',
    specClusterName: 'Pulsar',
    dbType: DBTypes.PULSAR,
    moduleId: 'bigdata',
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
  },
  [ClusterTypes.DORIS]: {
    id: ClusterTypes.DORIS,
    name: 'Doris',
    specClusterName: 'Doris',
    dbType: DBTypes.DORIS,
    moduleId: 'bigdata',
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
    [ClusterTypes.DORIS]: {
      id: ClusterTypes.DORIS,
      name: 'Doris',
      dbType: DBTypes.DORIS,
      moduleId: 'bigdata',
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
    },
  },
};

const mongodb: InfoType = {
  [ClusterTypes.MONGO_REPLICA_SET]: {
    id: ClusterTypes.MONGO_REPLICA_SET,
    name: t('Mongo副本集'),
    specClusterName: 'MongoDB',
    dbType: DBTypes.MONGODB,
    moduleId: 'mongodb',
    machineList: [
      {
        id: MachineTypes.MONGODB,
        name: '副本集/ShardSvr',
      },
    ],
  },
  [ClusterTypes.MONGO_SHARED_CLUSTER]: {
    id: ClusterTypes.MONGO_SHARED_CLUSTER,
    name: t('Mongo 分片集群'),
    specClusterName: 'MongoDB',
    dbType: DBTypes.MONGODB,
    moduleId: 'mongodb',
    machineList: [
      {
        id: MachineTypes.MONGOS,
        name: 'Mongos',
      },
      {
        id: MachineTypes.MONGODB,
        name: '副本集/ShardSvr',
      },
      {
        id: MachineTypes.MONGO_CONFIG,
        name: 'ConfigSvr',
      },
    ],
  },
};

const sqlserver: InfoType = {
  [ClusterTypes.SQLSERVER_SINGLE]: {
    id: ClusterTypes.SQLSERVER_SINGLE,
    name: t('SQLServer单节点'),
    specClusterName: 'SQLServer',
    dbType: DBTypes.SQLSERVER,
    moduleId: 'sqlserver',
    machineList: [
      {
        id: MachineTypes.SQLSERVER,
        name: t('后端存储'),
      },
    ],
  },
  [ClusterTypes.SQLSERVER_HA]: {
    id: ClusterTypes.SQLSERVER_HA,
    name: t('SQLServer主从'),
    specClusterName: 'SQLServer',
    dbType: DBTypes.SQLSERVER,
    moduleId: 'sqlserver',
    machineList: [
      {
        id: MachineTypes.SQLSERVER,
        name: t('后端存储'),
      },
    ],
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
