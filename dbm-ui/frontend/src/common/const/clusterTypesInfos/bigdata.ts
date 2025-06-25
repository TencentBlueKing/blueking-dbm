import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type ClusterTypeInfo } from './index';

export const bigdata: ClusterTypeInfo = {
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
