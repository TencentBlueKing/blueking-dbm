import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type InfoType } from './index';

export const spider: InfoType = {
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
