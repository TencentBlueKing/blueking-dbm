import { t } from '@locales/index';

import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type DbInfoType } from './index';

export const redis: DbInfoType = {
  [DBTypes.REDIS]: {
    id: DBTypes.REDIS,
    machineList: [
      {
        label: 'Proxy',
        value: MachineTypes.REDIS_PROXY,
      },
      {
        label: t('TendisCache/RedisCluster/Redis主从 后端存储'),
        value: MachineTypes.REDIS_TENDIS_CACHE,
      },
      {
        label: t('TendisSSD后端存储'),
        value: MachineTypes.REDIS_TENDIS_SSD,
      },
      {
        label: t('TendisPlus后端存储'),
        value: MachineTypes.REDIS_TENDIS_PLUS,
      },
      // {
      //   label: 'RedisCluster',
      //   value: MachineTypes.REDIS_CLUSTER, // 合入 REDIS_TENDIS_CACHE except 部署方案维持
      // },
      // {
      //   label: t('Redis主从'),
      //   value: MachineTypes.REDIS_INSTANCE, // 合入 REDIS_TENDIS_CACHE
      // },
    ],
    moduleId: 'redis',
    name: 'Redis',
  },
};
