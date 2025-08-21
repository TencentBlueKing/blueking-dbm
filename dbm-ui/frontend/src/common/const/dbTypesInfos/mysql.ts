import { t } from '@locales/index';

import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type DbInfoType } from './index';

export const mysql: DbInfoType = {
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
    routeIndexName: 'MysqlManage',
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
    routeIndexName: 'SpiderManage',
  },
};
