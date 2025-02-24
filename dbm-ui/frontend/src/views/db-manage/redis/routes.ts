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

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

const redisInstallModuleRoute = {
  component: () => import('@views/db-manage/redis/install-module/Index.vue'),
  meta: {
    navName: t('安装 Module'),
  },
  name: 'RedisInstallModule',
  path: 'install-module/:page?',
};

const redisCapacityChangeRoute = {
  component: () => import('@views/db-manage/redis/capacity-change/Index.vue'),
  meta: {
    navName: t('集群容量变更'),
  },
  name: 'RedisCapacityChange',
  path: 'capacity-change/:page?',
};

const redisProxyScaleUpRoute = {
  component: () => import('@views/db-manage/redis/proxy-scale-up/Index.vue'),
  meta: {
    navName: t('扩容接入层'),
  },
  name: 'RedisProxyScaleUp',
  path: 'proxy-scale-up/:page?',
};

const redisProxyScaleDownRoute = {
  component: () => import('@views/db-manage/redis/proxy-scale-down/Index.vue'),
  meta: {
    navName: t('缩容接入层'),
  },
  name: 'RedisProxyScaleDown',
  path: 'proxy-scale-down/:page?',
};

const redisDBCreateSlaveRoute = {
  component: () => import('@views/db-manage/redis/db-create-slave/Index.vue'),
  meta: {
    navName: t('重建从库'),
  },
  name: 'RedisDBCreateSlave',
  path: 'db-create-slave/:page?',
};

const redisMasterFailoverRoute = {
  component: () => import('@views/db-manage/redis/master-failover/Index.vue'),
  meta: {
    navName: t('主从切换'),
  },
  name: 'RedisMasterFailover',
  path: 'master-failover/:page?',
};

const redisDBReplaceRoute = {
  component: () => import('@views/db-manage/redis/db-replace/Index.vue'),
  meta: {
    navName: t('整机替换'),
  },
  name: 'RedisDBReplace',
  path: 'db-replace/:page?',
};

const redisMigrateRoute = {
  component: () => import('@views/db-manage/redis/migrate/Index.vue'),
  meta: {
    navName: t('迁移'),
  },
  name: 'RedisMigrate',
  path: 'db-migrate/:page?',
};

const redisClusterShardUpdateRoute = {
  component: () => import('@views/db-manage/redis/cluster-shard-update/Index.vue'),
  meta: {
    navName: t('集群分片变更'),
  },
  name: 'RedisClusterShardUpdate',
  path: 'cluster-shard-update/:page?',
};

const redisClusterTypeUpdateRoute = {
  component: () => import('@views/db-manage/redis/cluster-type-update/Index.vue'),
  meta: {
    navName: t('集群类型变更'),
  },
  name: 'RedisClusterTypeUpdate',
  path: 'cluster-type-update/:page?',
};

const redisDBStructureRoute = {
  component: () => import('@views/db-manage/redis/db-structure/Index.vue'),
  meta: {
    navName: t('定点构造'),
  },
  name: 'RedisDBStructure',
  path: 'db-structure/:page?',
};

const redisStructureInstanceRoute = {
  component: () => import('@views/db-manage/redis/structure-instance/Index.vue'),
  meta: {
    navName: t('构造实例'),
  },
  name: 'RedisStructureInstance',
  path: 'structure-instance/:page?',
};

const redisRecoverFromInstanceRoute = {
  component: () => import('@views/db-manage/redis/recover-from-instance/Index.vue'),
  meta: {
    navName: t('以构造实例恢复'),
  },
  name: 'RedisRecoverFromInstance',
  path: 'recover-from-instance/:page?',
};

const redisDBDataCopyRoute = {
  component: () => import('@views/db-manage/redis/db-data-copy/Index.vue'),
  meta: {
    navName: t('数据复制'),
  },
  name: 'RedisDBDataCopy',
  path: 'db-data-copy/:page?',
};

const redisDBDataCopyRecordRoute = {
  component: () => import('@views/db-manage/redis/db-data-copy-record/Index.vue'),
  meta: {
    navName: t('数据复制记录'),
  },
  name: 'RedisDBDataCopyRecord',
  path: 'db-data-copy-record/:page?',
};

const redisVersionUpgradeRoute = {
  component: () => import('@views/db-manage/redis/version-upgrade/Index.vue'),
  meta: {
    navName: t('版本升级'),
  },
  name: 'RedisVersionUpgrade',
  path: 'version-upgrade/:page?',
};

const redisWebconsoleRoute = {
  component: () => import('@views/db-manage/redis/webconsole/Index.vue'),
  meta: {
    navName: 'Webconsole',
  },
  name: 'RedisWebconsole',
  path: 'webconsole',
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
    children: [] as RouteRecordRaw[],
    component: () => import('@views/db-manage/redis/toolbox/Index.vue'),
    meta: {
      fullscreen: true,
      navName: t('工具箱'),
    },
    name: 'RedisToolbox',
    path: 'toolbox',
    redirect: {
      name: '',
    },
  },
  {
    component: () => import('@views/db-manage/redis/data-check-repair/Index.vue'),
    meta: {
      navName: t('数据校验修复'),
    },
    name: 'RedisToolboxDataCheckRepair',
    path: 'data-check-repair/:page?',
  },
];

const redisInstanceListRoute = {
  component: () => import('@views/db-manage/redis/instance-list/Index.vue'),
  meta: {
    fullscreen: true,
    navName: t('Redis 集群实例视图'),
  },
  name: 'DatabaseRedisInstanceList',
  path: 'instance-list',
};

const redisHaInstanceListRoute = {
  component: () => import('@views/db-manage/redis/instance-ha-list/Index.vue'),
  meta: {
    fullscreen: true,
    navName: t('Redis 主从实例视图'),
  },
  name: 'DatabaseRedisHaInstanceList',
  path: 'instance-ha-list',
};

const redisDatabaseHaList = {
  component: () => import('@views/db-manage/redis/cluster-ha-list/Index.vue'),
  meta: {
    fullscreen: true,
    navName: t('Redis 主从管理'),
  },
  name: 'DatabaseRedisHaList',
  path: 'cluster-ha-list',
};

const routes: RouteRecordRaw[] = [
  {
    children: [
      {
        component: () => import('@views/db-manage/redis/cluster-list/Index.vue'),
        meta: {
          fullscreen: true,
          navName: t('Redis_集群管理'),
        },
        name: 'DatabaseRedisList',
        path: 'cluster-list',
      },
    ],
    component: () => import('@views/db-manage/redis/Index.vue'),
    meta: {
      navName: t('Redis_集群管理'),
    },
    name: 'RedisManage',
    path: 'redis',
    redirect: {
      name: 'DatabaseRedisList',
    },
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
