import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type InfoType } from './index';

export const sqlserver: InfoType = {
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
