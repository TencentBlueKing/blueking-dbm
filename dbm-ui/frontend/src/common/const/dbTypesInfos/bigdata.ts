import { t } from '@locales/index';

import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type DbInfoType } from './index';

export const bigdata: DbInfoType = {
  [DBTypes.DORIS]: {
    icon: 'doris',
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
    routeIndexName: 'DorisManage',
  },
  [DBTypes.ES]: {
    icon: 'es',
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
    routeIndexName: 'EsManage',
  },
  [DBTypes.HDFS]: {
    icon: 'hdfs',
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
    routeIndexName: 'HdfsManage',
  },
  [DBTypes.INFLUXDB]: {
    icon: 'influxdb',
    id: DBTypes.INFLUXDB,
    machineList: [
      {
        label: t('后端存储'),
        value: MachineTypes.INFLUXDB,
      },
    ],
    moduleId: 'bigdata',
    name: 'InfuxDB',
    routeIndexName: 'InfluxDBManage',
  },
  [DBTypes.KAFKA]: {
    icon: 'kafka',
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
    routeIndexName: 'KafkaManage',
  },
  [DBTypes.PULSAR]: {
    icon: 'pulsar',
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
    routeIndexName: 'PulsarManage',
  },
  [DBTypes.RIAK]: {
    icon: 'cluster',
    id: DBTypes.RIAK,
    machineList: [
      {
        label: t('后端存储'),
        value: MachineTypes.RIAK,
      },
    ],
    moduleId: 'bigdata',
    name: 'Riak',
    routeIndexName: 'RiakManage',
  },
};
