import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type ClusterTypeInfo } from './index';

export const mongodb: ClusterTypeInfo = {
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
