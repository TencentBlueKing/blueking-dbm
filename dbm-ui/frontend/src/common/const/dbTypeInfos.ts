import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

import { DBTypes } from './dbTypes';
import { MachineTypes } from './machineTypes';

export interface InfoItem {
  id: DBTypes;
  name: string;
  moduleId: ExtractedControllerDataKeys;
  machineList: {
    label: string;
    value: MachineTypes;
  }[];
}

type InfoType = {
  [x in DBTypes]?: InfoItem;
};

type RequiredInfoType = {
  [x in DBTypes]: InfoItem;
};

const mysql: InfoType = {
  [DBTypes.MYSQL]: {
    id: DBTypes.MYSQL,
    name: 'MySQL',
    moduleId: 'mysql',
    machineList: [
      {
        label: 'Proxy',
        value: MachineTypes.MYSQL_PROXY,
      },
      {
        label: t('后端存储'),
        value: MachineTypes.MYSQL_BACKEND,
      },
    ],
  },
  [DBTypes.TENDBCLUSTER]: {
    id: DBTypes.TENDBCLUSTER,
    name: 'TenDBCluster',
    moduleId: 'mysql',
    machineList: [
      {
        label: t('接入层Master'),
        value: MachineTypes.TENDBCLUSTER_PROXY,
      },
      {
        label: t('后端存储'),
        value: MachineTypes.TENDBCLUSTER_BACKEND,
      },
    ],
  },
};
const redis: InfoType = {
  [DBTypes.REDIS]: {
    id: DBTypes.REDIS,
    name: 'Redis',
    moduleId: 'redis',
    machineList: [
      {
        label: 'Proxy',
        value: MachineTypes.REDIS_PROXY,
      },
      {
        label: t('TendisCache/RedisCluster/Redis主从 后端存储'),
        value: MachineTypes.REDIS_TENDIS_CACHE,
      },
      {
        label: t('TendisSSD后端存储'),
        value: MachineTypes.REDIS_TENDIS_SSD,
      },
      {
        label: t('TendisPlus后端存储'),
        value: MachineTypes.REDIS_TENDIS_PLUS,
      },
      // {
      //   label: 'RedisCluster',
      //   value: MachineTypes.REDIS_CLUSTER, // 合入 REDIS_TENDIS_CACHE except 部署方案维持
      // },
      // {
      //   label: t('Redis主从'),
      //   value: MachineTypes.REDIS_INSTANCE, // 合入 REDIS_TENDIS_CACHE
      // },
    ],
  },
};
const mongo: InfoType = {
  [DBTypes.MONGODB]: {
    id: DBTypes.MONGODB,
    name: 'MongoDB',
    moduleId: 'mongodb',
    machineList: [
      {
        label: 'ConfigSvr',
        value: MachineTypes.MONGO_CONFIG,
      },
      {
        label: 'Mongos',
        value: MachineTypes.MONGOS,
      },
      {
        label: t('副本集/ShardSvr'),
        value: MachineTypes.MONGODB,
      },
    ],
  },
};
const sqlserver: InfoType = {
  [DBTypes.SQLSERVER]: {
    id: DBTypes.SQLSERVER,
    name: 'SQLServer',
    moduleId: 'sqlserver',
    machineList: [
      {
        label: t('后端存储'),
        value: MachineTypes.SQLSERVER,
      },
    ],
  },
};
const bigdata: InfoType = {
  [DBTypes.ES]: {
    id: DBTypes.ES,
    name: 'ElasticSearch',
    moduleId: 'bigdata',
    machineList: [
      {
        label: t('Master节点'),
        value: MachineTypes.ES_MASTER,
      },
      {
        label: t('Client节点'),
        value: MachineTypes.ES_CLIENT,
      },
      {
        label: t('冷_热节点'),
        value: MachineTypes.ES_DATANODE,
      },
    ],
  },
  [DBTypes.KAFKA]: {
    id: DBTypes.KAFKA,
    name: 'Kafka',
    moduleId: 'bigdata',
    machineList: [
      {
        label: t('Zookeeper节点'),
        value: MachineTypes.KAFKA_ZOOKEEPER,
      },
      {
        label: t('Broker节点'),
        value: MachineTypes.KAFKA_BROKER,
      },
    ],
  },
  [DBTypes.HDFS]: {
    id: DBTypes.HDFS,
    name: 'HDFS',
    moduleId: 'bigdata',
    machineList: [
      {
        label: t('DataNode节点'),
        value: MachineTypes.HDFS_DATANODE,
      },
      {
        label: t('NameNode_Zookeeper_JournalNode节点'),
        value: MachineTypes.HDFS_MASTER,
      },
    ],
  },
  [DBTypes.INFLUXDB]: {
    id: DBTypes.INFLUXDB,
    name: 'InfuxDB',
    moduleId: 'bigdata',
    machineList: [
      {
        label: t('后端存储'),
        value: MachineTypes.INFLUXDB,
      },
    ],
  },
  [DBTypes.RIAK]: {
    id: DBTypes.RIAK,
    name: 'Riak',
    moduleId: 'bigdata',
    machineList: [
      {
        label: t('后端存储'),
        value: MachineTypes.RIAK,
      },
    ],
  },
  [DBTypes.PULSAR]: {
    id: DBTypes.PULSAR,
    name: 'Pulsar',
    moduleId: 'bigdata',
    machineList: [
      {
        label: t('Bookkeeper节点'),
        value: MachineTypes.PULSAR_BOOKKEEPER,
      },
      {
        label: t('Zookeeper节点'),
        value: MachineTypes.PULSAR_ZOOKEEPER,
      },
      {
        label: t('Broker节点'),
        value: MachineTypes.PULSAR_BROKER,
      },
    ],
  },
  [DBTypes.DORIS]: {
    id: DBTypes.DORIS,
    name: 'Doris',
    moduleId: 'bigdata',
    machineList: [
      {
        label: t('Follower节点'),
        value: MachineTypes.DORIS_FOLLOWER,
      },
      {
        label: t('Observer节点'),
        value: MachineTypes.DORIS_OBSERVER,
      },
      {
        label: t('冷/热节点'),
        value: MachineTypes.DORIS_BACKEND,
      },
    ],
  },
};
export const DBTypeInfos = {
  ...mysql,
  ...redis,
  ...mongo,
  ...sqlserver,
  ...bigdata,
} as RequiredInfoType;
