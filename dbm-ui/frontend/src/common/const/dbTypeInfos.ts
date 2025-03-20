import type { ExtractedControllerDataKeys } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

import { DBTypes } from './dbTypes';
import { MachineTypes } from './machineTypes';

export interface InfoItem {
  id: DBTypes;
  machineList: {
    label: string;
    value: MachineTypes;
  }[];
  moduleId: ExtractedControllerDataKeys;
  name: string;
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
    moduleId: 'mysql',
    name: 'MySQL',
  },
  [DBTypes.TENDBCLUSTER]: {
    id: DBTypes.TENDBCLUSTER,
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
    moduleId: 'mysql',
    name: 'TenDBCluster',
  },
};
const redis: InfoType = {
  [DBTypes.REDIS]: {
    id: DBTypes.REDIS,
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
    moduleId: 'redis',
    name: 'Redis',
  },
};
const mongo: InfoType = {
  [DBTypes.MONGODB]: {
    id: DBTypes.MONGODB,
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
    moduleId: 'mongodb',
    name: 'MongoDB',
  },
};
const sqlserver: InfoType = {
  [DBTypes.SQLSERVER]: {
    id: DBTypes.SQLSERVER,
    machineList: [
      {
        label: t('后端存储'),
        value: MachineTypes.SQLSERVER,
      },
    ],
    moduleId: 'sqlserver',
    name: 'SQLServer',
  },
};
const bigdata: InfoType = {
  [DBTypes.DORIS]: {
    id: DBTypes.DORIS,
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
    moduleId: 'bigdata',
    name: 'Doris',
  },
  [DBTypes.ES]: {
    id: DBTypes.ES,
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
    moduleId: 'bigdata',
    name: 'ElasticSearch',
  },
  [DBTypes.HDFS]: {
    id: DBTypes.HDFS,
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
    moduleId: 'bigdata',
    name: 'HDFS',
  },
  [DBTypes.INFLUXDB]: {
    id: DBTypes.INFLUXDB,
    machineList: [
      {
        label: t('后端存储'),
        value: MachineTypes.INFLUXDB,
      },
    ],
    moduleId: 'bigdata',
    name: 'InfuxDB',
  },
  [DBTypes.KAFKA]: {
    id: DBTypes.KAFKA,
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
    moduleId: 'bigdata',
    name: 'Kafka',
  },
  [DBTypes.PULSAR]: {
    id: DBTypes.PULSAR,
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
    moduleId: 'bigdata',
    name: 'Pulsar',
  },
  [DBTypes.RIAK]: {
    id: DBTypes.RIAK,
    machineList: [
      {
        label: t('后端存储'),
        value: MachineTypes.RIAK,
      },
    ],
    moduleId: 'bigdata',
    name: 'Riak',
  },
};
export const DBTypeInfos = {
  ...mysql,
  ...redis,
  ...mongo,
  ...sqlserver,
  ...bigdata,
} as RequiredInfoType;
