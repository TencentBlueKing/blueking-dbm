// import { t } from '@locales/index';

import { DBTypes } from '../dbTypes';

// import { MachineTypes } from '../machineTypes';
import { type DbInfoType } from './index';

export const oracle: DbInfoType = {
  [DBTypes.ORACLE]: {
    id: DBTypes.ORACLE,
    machineList: [],
    moduleId: 'oracle',
    name: 'Oracle',
    routeIndexName: 'OracleManage',
  },
};
