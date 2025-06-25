import { t } from '@locales/index';

import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type DbInfoType } from './index';

export const bigdata: DbInfoType = {
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
