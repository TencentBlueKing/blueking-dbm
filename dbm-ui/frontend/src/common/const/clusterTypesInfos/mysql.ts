import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type ClusterTypeInfo } from './index';

export const mysql: ClusterTypeInfo = {
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
  // eslint-disable-next-line perfectionist/sort-objects
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
  // eslint-disable-next-line perfectionist/sort-objects
  [ClusterTypes.TENDBCLUSTER]: {
    dbType: DBTypes.TENDBCLUSTER,
    id: ClusterTypes.TENDBCLUSTER,
    machineList: [
      {
        id: MachineTypes.TENDBCLUSTER_PROXY,
        name: t('接入层'),
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
