import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type InfoType } from './index';

export const mysql: InfoType = {
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
