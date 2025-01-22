/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import type { RouteRecordRaw } from 'vue-router';

import FunctionControllModel, {
  type ExtractedControllerDataKeys,
  type RedisFunctions,
} from '@services/model/function-controller/functionController';

import { DBTypes, TicketTypes } from '@common/const';

import { checkDbConsole, createToolboxRoute } from '@utils';

import { t } from '@locales/index';

const { createRouteItem } = createToolboxRoute(DBTypes.REDIS);

const redisInstallModuleRoute = {
  name: 'RedisInstallModule',
  path: 'install-module/:page?',
  meta: {
    navName: t('安装 Module'),
  },
  component: () => import('@views/db-manage/redis/install-module/Index.vue'),
};

const redisCapacityChangeRoute = createRouteItem(TicketTypes.REDIS_SCALE_UPDOWN, t('集群容量变更'));

const redisProxyScaleUpRoute = {
  name: 'RedisProxyScaleUp',
  path: 'proxy-scale-up/:page?',
  meta: {
    navName: t('扩容接入层'),
  },
  component: () => import('@views/db-manage/redis/proxy-scale-up/Index.vue'),
};

const redisProxyScaleDownRoute = createRouteItem(TicketTypes.REDIS_PROXY_SCALE_DOWN, t('缩容接入层'));

// const redisDBCreateSlaveRoute = {
//   name: 'RedisDBCreateSlave',
//   path: 'db-create-slave/:page?',
//   meta: {
//     navName: t('重建从库'),
//   },
//   component: () => import('@views/db-manage/redis/db-create-slave/Index.vue'),
// };
const redisDBCreateSlaveRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_ADD_SLAVE, t('重建从库'));

// const redisMasterFailoverRoute = {
//   name: 'RedisMasterFailover',
//   path: 'master-failover/:page?',
//   meta: {
//     navName: t('主从切换'),
//   },
//   component: () => import('@views/db-manage/redis/master-failover/Index.vue'),
// };
const redisMasterFailoverRoute = createRouteItem(TicketTypes.REDIS_MASTER_SLAVE_SWITCH, t('主从切换'));

const redisDBReplaceRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_CUTOFF, t('整机替换'));

const redisMigrateRoute = {
  name: 'RedisMigrate',
  path: 'db-migrate/:page?',
  meta: {
    navName: t('迁移'),
  },
  component: () => import('@views/db-manage/redis/migrate/Index.vue'),
};

const redisClusterShardUpdateRoute = {
  name: 'RedisClusterShardUpdate',
  path: 'cluster-shard-update/:page?',
  meta: {
    navName: t('集群分片变更'),
  },
  component: () => import('@views/db-manage/redis/cluster-shard-update/Index.vue'),
};

const redisClusterTypeUpdateRoute = {
  name: 'RedisClusterTypeUpdate',
  path: 'cluster-type-update/:page?',
  meta: {
    navName: t('集群类型变更'),
  },
  component: () => import('@views/db-manage/redis/cluster-type-update/Index.vue'),
};

const redisDBStructureRoute = {
  name: 'RedisDBStructure',
  path: 'db-structure/:page?',
  meta: {
    navName: t('定点构造'),
  },
  component: () => import('@views/db-manage/redis/db-structure/Index.vue'),
};

const redisStructureInstanceRoute = {
  name: 'RedisStructureInstance',
  path: 'structure-instance/:page?',
  meta: {
    navName: t('构造实例'),
  },
  component: () => import('@views/db-manage/redis/structure-instance/Index.vue'),
};

const redisRecoverFromInstanceRoute = {
  name: 'RedisRecoverFromInstance',
  path: 'recover-from-instance/:page?',
  meta: {
    navName: t('以构造实例恢复'),
  },
  component: () => import('@views/db-manage/redis/recover-from-instance/Index.vue'),
};

// const redisDBDataCopyRoute = {
//   name: 'RedisDBDataCopy',
//   path: 'db-data-copy/:page?',
//   meta: {
//     navName: t('数据复制'),
//   },
//   component: () => import('@views/db-manage/redis/db-data-copy/Index.vue'),
// };
const redisDBDataCopyRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_DATA_COPY, t('数据复制'));

const redisDBDataCopyRecordRoute = {
  name: 'RedisDBDataCopyRecord',
  path: 'db-data-copy-record/:page?',
  meta: {
    navName: t('数据复制记录'),
  },
  component: () => import('@views/db-manage/redis/db-data-copy-record/Index.vue'),
};

// const redisVersionUpgradeRoute = {
//   name: 'RedisVersionUpgrade',
//   path: 'version-upgrade/:page?',
//   meta: {
//     navName: t('版本升级'),
//   },
//   component: () => import('@views/db-manage/redis/version-upgrade/Index.vue'),
// };
const redisVersionUpgradeRoute = createRouteItem(TicketTypes.REDIS_VERSION_UPDATE_ONLINE, t('版本升级'));

const redisWebconsoleRoute = {
  name: 'RedisWebconsole',
  path: 'webconsole',
  meta: {
    navName: 'Webconsole',
  },
  component: () => import('@views/db-manage/redis/webconsole/Index.vue'),
};

const toolboxDbConsoleRouteMap = {
  'redis.toolbox.installModule': redisInstallModuleRoute,
  'redis.toolbox.capacityChange': redisCapacityChangeRoute,
  'redis.toolbox.proxyScaleUp': redisProxyScaleUpRoute,
  'redis.toolbox.proxyScaleDown': redisProxyScaleDownRoute,
  'redis.toolbox.clusterShardChange': redisClusterShardUpdateRoute,
  'redis.toolbox.clusterTypeChange': redisClusterTypeUpdateRoute,
  'redis.toolbox.slaveRebuild': redisDBCreateSlaveRoute,
  'redis.toolbox.masterSlaveSwap': redisMasterFailoverRoute,
  'redis.toolbox.dbReplace': redisDBReplaceRoute,
  'redis.toolbox.migrate': redisMigrateRoute,
  'redis.toolbox.versionUpgrade': redisVersionUpgradeRoute,
  'redis.toolbox.rollback': redisDBStructureRoute,
  'redis.toolbox.rollbackRecord': redisStructureInstanceRoute,
  'redis.toolbox.recoverFromInstance': redisRecoverFromInstanceRoute,
  'redis.toolbox.dataCopy': redisDBDataCopyRoute,
  'redis.toolbox.dataCopyRecord': redisDBDataCopyRecordRoute,
  'redis.toolbox.webconsole': redisWebconsoleRoute,
};

const toolboxRoutes = [
  {
    name: 'RedisToolbox',
    path: 'toolbox',
    redirect: {
      name: '',
    },
    meta: {
      navName: t('工具箱'),
      fullscreen: true,
    },
    component: () => import('@views/db-manage/redis/toolbox/Index.vue'),
    children: [] as RouteRecordRaw[],
  },
  // {
  //   name: 'RedisToolboxDataCheckRepair',
  //   path: 'data-check-repair/:page?',
  //   meta: {
  //     navName: t('数据校验修复'),
  //   },
  //   component: () => import('@views/db-manage/redis/data-check-repair/Index.vue'),
  // },
  createRouteItem(TicketTypes.REDIS_DATACOPY_CHECK_REPAIR, t('数据校验修复')),
];

const redisInstanceListRoute = {
  name: 'DatabaseRedisInstanceList',
  path: 'instance-list',
  meta: {
    navName: t('Redis 集群实例视图'),
    fullscreen: true,
  },
  component: () => import('@views/db-manage/redis/instance-list/Index.vue'),
};

const redisHaInstanceListRoute = {
  name: 'DatabaseRedisHaInstanceList',
  path: 'instance-ha-list',
  meta: {
    navName: t('Redis 主从实例视图'),
    fullscreen: true,
  },
  component: () => import('@views/db-manage/redis/instance-ha-list/Index.vue'),
};

const redisDatabaseHaList = {
  name: 'DatabaseRedisHaList',
  path: 'cluster-ha-list',
  meta: {
    navName: t('Redis 主从管理'),
    fullscreen: true,
  },
  component: () => import('@views/db-manage/redis/cluster-ha-list/Index.vue'),
};

const routes: RouteRecordRaw[] = [
  {
    name: 'RedisManage',
    path: 'redis',
    meta: {
      navName: t('Redis_集群管理'),
    },
    redirect: {
      name: 'DatabaseRedisList',
    },
    component: () => import('@views/db-manage/redis/Index.vue'),
    children: [
      {
        name: 'DatabaseRedisList',
        path: 'cluster-list',
        meta: {
          navName: t('Redis_集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/redis/cluster-list/Index.vue'),
      },
    ],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<RedisFunctions, 'redis'>('redis');

  if (controller.redis !== true) {
    return [];
  }

  if (checkDbConsole('redis.instanceManage')) {
    routes[0].children!.push(redisInstanceListRoute);
  }

  if (checkDbConsole('redis.haInstanceManage')) {
    routes[0].children!.push(redisHaInstanceListRoute);
  }

  if (checkDbConsole('redis.haClusterManage')) {
    routes[0].children!.push(redisDatabaseHaList);
  }

  // const renderRoutes = routes.find((item) => item.name === 'RedisManage');
  // if (!renderRoutes) {
  //   return routes;
  // }

  if (controller.toolbox) {
    Object.entries(toolboxDbConsoleRouteMap).forEach(([key, routeItem]) => {
      const dbConsoleValue = key as ExtractedControllerDataKeys;
      if (!funControllerData[dbConsoleValue] || funControllerData[dbConsoleValue].is_enabled) {
        toolboxRoutes[0].children!.push(routeItem);
        if (routeItem.name === 'RedisCapacityChange') {
          toolboxRoutes[0].redirect!.name = 'RedisCapacityChange';
        }
      }
    });

    if (!toolboxRoutes[0].redirect!.name) {
      toolboxRoutes[0].redirect!.name = (toolboxRoutes[0].children![0]?.name as string) ?? '';
    }
    routes[0].children?.push(...toolboxRoutes);
  }

  return routes;
}
