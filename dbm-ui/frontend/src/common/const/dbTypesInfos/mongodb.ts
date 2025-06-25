import { t } from '@locales/index';

import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type DbInfoType } from './index';

export const mongodb: DbInfoType = {
  [DBTypes.MONGODB]: {
    id: DBTypes.MONGODB,
    machineList: [
      {
        label: 'ConfigSvr',
        value: MachineTypes.MONGO_CONFIG,
      },
      {
        label: 'Mongos',
        value: MachineTypes.MONGOS,
      },
      {
        label: t('副本集/ShardSvr'),
        value: MachineTypes.MONGODB,
      },
    ],
    moduleId: 'mongodb',
    name: 'MongoDB',
  },
};
