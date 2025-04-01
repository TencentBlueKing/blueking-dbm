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
  path: 'install-module/:page?',
  name: 'RedisInstallModule',
  meta: {
    navName: t('安装 Module'),
  },
  component: () => import('@views/db-manage/redis/install-module/Index.vue'),
};

const redisCapacityChangeRoute = createRouteItem(TicketTypes.REDIS_SCALE_UPDOWN, t('集群容量变更'));

const redisProxyScaleUpRoute = {
  path: 'proxy-scale-up/:page?',
  name: 'RedisProxyScaleUp',
  meta: {
    navName: t('扩容接入层'),
  },
  component: () => import('@views/db-manage/redis/proxy-scale-up/Index.vue'),
};

const redisProxyScaleDownRoute = createRouteItem(TicketTypes.REDIS_PROXY_SCALE_DOWN, t('缩容接入层'));

const redisDBCreateSlaveRoute = {
  path: 'db-create-slave/:page?',
  name: 'RedisDBCreateSlave',
  meta: {
    navName: t('重建从库'),
  },
  component: () => import('@views/db-manage/redis/db-create-slave/Index.vue'),
};

const redisMasterFailoverRoute = {
  path: 'master-failover/:page?',
  name: 'RedisMasterFailover',
  meta: {
    navName: t('主从切换'),
  },
  component: () => import('@views/db-manage/redis/master-failover/Index.vue'),
};

const redisDBReplaceRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_CUTOFF, t('整机替换'));

const redisMigrateRoute = {
  path: 'db-migrate/:page?',
  name: 'RedisMigrate',
  meta: {
    navName: t('迁移'),
  },
  component: () => import('@views/db-manage/redis/migrate/Index.vue'),
};

const redisClusterShardUpdateRoute = {
  path: 'cluster-shard-update/:page?',
  name: 'RedisClusterShardUpdate',
  meta: {
    navName: t('集群分片变更'),
  },
  component: () => import('@views/db-manage/redis/cluster-shard-update/Index.vue'),
};

const redisClusterTypeUpdateRoute = {
  path: 'cluster-type-update/:page?',
  name: 'RedisClusterTypeUpdate',
  meta: {
    navName: t('集群类型变更'),
  },
  component: () => import('@views/db-manage/redis/cluster-type-update/Index.vue'),
};

const redisDBStructureRoute = {
  path: 'db-structure/:page?',
  name: 'RedisDBStructure',
  meta: {
    navName: t('定点构造'),
  },
  component: () => import('@views/db-manage/redis/db-structure/Index.vue'),
};

const redisStructureInstanceRoute = {
  path: 'structure-instance/:page?',
  name: 'RedisStructureInstance',
  meta: {
    navName: t('构造实例'),
  },
  component: () => import('@views/db-manage/redis/structure-instance/Index.vue'),
};

const redisRecoverFromInstanceRoute = {
  path: 'recover-from-instance/:page?',
  name: 'RedisRecoverFromInstance',
  meta: {
    navName: t('以构造实例恢复'),
  },
  component: () => import('@views/db-manage/redis/recover-from-instance/Index.vue'),
};

const redisDBDataCopyRoute = {
  path: 'db-data-copy/:page?',
  name: 'RedisDBDataCopy',
  meta: {
    navName: t('数据复制'),
  },
  component: () => import('@views/db-manage/redis/db-data-copy/Index.vue'),
};

const redisDBDataCopyRecordRoute = {
  path: 'db-data-copy-record/:page?',
  name: 'RedisDBDataCopyRecord',
  meta: {
    navName: t('数据复制记录'),
  },
  component: () => import('@views/db-manage/redis/db-data-copy-record/Index.vue'),
};

const redisVersionUpgradeRoute = {
  path: 'version-upgrade/:page?',
  name: 'RedisVersionUpgrade',
  meta: {
    navName: t('版本升级'),
  },
  component: () => import('@views/db-manage/redis/version-upgrade/Index.vue'),
};

const redisWebconsoleRoute = {
  path: 'webconsole',
  name: 'RedisWebconsole',
  meta: {
    navName: 'Webconsole',
  },
  component: () => import('@views/db-manage/redis/webconsole/Index.vue'),
};

const toolboxDbConsoleRouteMap = {
  'redis.toolbox.capacityChange': redisCapacityChangeRoute,
  'redis.toolbox.clusterShardChange': redisClusterShardUpdateRoute,
  'redis.toolbox.clusterTypeChange': redisClusterTypeUpdateRoute,
  'redis.toolbox.dataCopy': redisDBDataCopyRoute,
  'redis.toolbox.dataCopyRecord': redisDBDataCopyRecordRoute,
  'redis.toolbox.dbReplace': redisDBReplaceRoute,
  'redis.toolbox.installModule': redisInstallModuleRoute,
  'redis.toolbox.masterSlaveSwap': redisMasterFailoverRoute,
  'redis.toolbox.migrate': redisMigrateRoute,
  'redis.toolbox.proxyScaleDown': redisProxyScaleDownRoute,
  'redis.toolbox.proxyScaleUp': redisProxyScaleUpRoute,
  'redis.toolbox.recoverFromInstance': redisRecoverFromInstanceRoute,
  'redis.toolbox.rollback': redisDBStructureRoute,
  'redis.toolbox.rollbackRecord': redisStructureInstanceRoute,
  'redis.toolbox.slaveRebuild': redisDBCreateSlaveRoute,
  'redis.toolbox.versionUpgrade': redisVersionUpgradeRoute,
  'redis.toolbox.webconsole': redisWebconsoleRoute,
};

const toolboxRoutes = [
  {
    path: 'toolbox',
    name: 'RedisToolbox',
    meta: {
      fullscreen: true,
      navName: t('工具箱'),
    },
    redirect: {
      name: '',
    },
    component: () => import('@views/db-manage/redis/toolbox/Index.vue'),
    children: [
      {
        path: 'toolbox-result/:ticketType?/:ticketId?',
        name: 'REDIS_ToolboxResult',
        component: () => import('@views/db-manage/common/create-ticket-success/Index.vue'),
      },
    ] as RouteRecordRaw[],
  },
  {
    path: 'data-check-repair/:page?',
    name: 'RedisToolboxDataCheckRepair',
    meta: {
      navName: t('数据校验修复'),
    },
    component: () => import('@views/db-manage/redis/data-check-repair/Index.vue'),
  },
];

const redisInstanceListRoute = {
  path: 'instance-list',
  name: 'DatabaseRedisInstanceList',
  meta: {
    fullscreen: true,
    navName: t('Redis 集群实例视图'),
  },
  component: () => import('@views/db-manage/redis/instance-list/Index.vue'),
};

const redisHaInstanceListRoute = {
  path: 'instance-ha-list',
  name: 'DatabaseRedisHaInstanceList',
  meta: {
    fullscreen: true,
    navName: t('Redis 主从实例视图'),
  },
  component: () => import('@views/db-manage/redis/instance-ha-list/Index.vue'),
};

const redisDatabaseHaList = {
  path: 'cluster-ha-list',
  name: 'DatabaseRedisHaList',
  meta: {
    fullscreen: true,
    navName: t('Redis 主从管理'),
  },
  component: () => import('@views/db-manage/redis/cluster-ha-list/Index.vue'),
};

const routes: RouteRecordRaw[] = [
  {
    path: 'redis',
    name: 'RedisManage',
    meta: {
      navName: t('Redis_集群管理'),
    },
    redirect: {
      name: 'DatabaseRedisList',
    },
    component: () => import('@views/db-manage/redis/Index.vue'),
    children: [
      {
        path: 'cluster-list',
        name: 'DatabaseRedisList',
        meta: {
          fullscreen: true,
          navName: t('Redis_集群管理'),
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
      toolboxRoutes[0].redirect!.name = 'RedisDBCreateSlave';
    }
    routes[0].children?.push(...toolboxRoutes);
  }

  return routes;
}
