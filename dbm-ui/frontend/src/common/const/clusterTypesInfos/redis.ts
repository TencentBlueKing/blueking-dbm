import { t } from '@locales/index';

import { ClusterTypes } from '../clusterTypes';
import { DBTypes } from '../dbTypes';
import { MachineTypes } from '../machineTypes';

import { type ClusterTypeInfo } from './index';

export const redis: ClusterTypeInfo = {
  [ClusterTypes.PREDIXY_REDIS_CLUSTER]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.PREDIXY_REDIS_CLUSTER,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_CACHE,
        name: t('TendisCache/RedisCluster/Redis主从 后端存储'),
      },
      {
        id: MachineTypes.REDIS_PROXY,
        name: 'Proxy',
      },
    ],
    moduleId: 'redis',
    name: 'RedisCluster',
    specClusterName: 'Redis',
  },
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_PLUS,
        name: t('TendisPlus后端存储'),
      },
      {
        id: MachineTypes.REDIS_PROXY,
        name: 'Proxy',
      },
    ],
    moduleId: 'redis',
    name: 'Tendisplus',
    specClusterName: 'Redis',
  },
  [ClusterTypes.REDIS_INSTANCE]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.REDIS_INSTANCE,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_CACHE,
        name: t('TendisCache/RedisCluster/Redis主从 后端存储'),
      },
    ],
    moduleId: 'redis',
    name: t('Redis主从'),
    specClusterName: 'Redis',
  },
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_CACHE,
        name: t('TendisCache/RedisCluster/Redis主从 后端存储'),
      },
      {
        id: MachineTypes.REDIS_PROXY,
        name: 'Proxy',
      },
    ],
    moduleId: 'redis',
    name: 'TendisCache',
    specClusterName: 'Redis',
  },
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
    dbType: DBTypes.REDIS,
    id: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    machineList: [
      {
        id: MachineTypes.REDIS_TENDIS_CACHE,
        name: t('TendisCache/RedisCluster/Redis主从 后端存储'),
      },
      {
        id: MachineTypes.REDIS_PROXY,
        name: 'Proxy',
      },
    ],
    moduleId: 'redis',
    name: 'TendisSSD',
    specClusterName: 'Redis',
  },
};
