import { t } from '@locales/index';

import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type DbInfoType } from './index';

export const sqlserver: DbInfoType = {
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
