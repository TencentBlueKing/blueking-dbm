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

const redisClusterReInstallDbmonRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_REINSTALL_DBMON, t('集群标准化'));
const redisInstallModuleRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_LOAD_MODULES, t('安装 Module'));
const redisCapacityChangeRoute = createRouteItem(TicketTypes.REDIS_SCALE_UPDOWN, t('集群容量变更'));
const redisProxyScaleUpRoute = createRouteItem(TicketTypes.REDIS_PROXY_SCALE_UP, t('扩容接入层'));
const redisProxyScaleDownRoute = createRouteItem(TicketTypes.REDIS_PROXY_SCALE_DOWN, t('缩容接入层'));
const redisDBCreateSlaveRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_ADD_SLAVE, t('重建从库'));
const redisMasterFailoverRoute = createRouteItem(TicketTypes.REDIS_MASTER_SLAVE_SWITCH, t('主从切换'));
const redisDBReplaceRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_CUTOFF, t('整机替换'));
const redisClusterMigrateRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_INS_MIGRATE, t('迁移'));
const redisSingleMigrateRoute = createRouteItem(TicketTypes.REDIS_SINGLE_INS_MIGRATE, t('迁移'));
const redisClusterShardUpdateRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE, t('集群分片变更'));
const redisShardAddRoute = createRouteItem(TicketTypes.REDIS_SHARD_ADD, t('集群分片变更（Slot迁移）'));
const redisShardReduceRoute = createRouteItem(TicketTypes.REDIS_SHARD_REDUCE, t('集群分片变更（Slot迁移）'));
const redisClusterTypeUpdateRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_TYPE_UPDATE, t('集群类型变更'));
const redisDataStructureRoute = createRouteItem(TicketTypes.REDIS_DATA_STRUCTURE, t('定点构造'));
const redisClusterRollbackDataCopyRoute = createRouteItem(
  TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
  t('以构造实例恢复'),
);

const redisStructureInstanceRoute = {
  path: 'structure-instance/:page?',
  name: 'RedisStructureInstance',
  meta: {
    navName: t('构造实例'),
  },
  component: () => import('@views/db-manage/redis/structure-instance/Index.vue'),
};

const redisDBDataCopyRoute = createRouteItem(TicketTypes.REDIS_CLUSTER_DATA_COPY, t('数据复制'));

const redisDBDataCopyRecordRoute = {
  path: 'db-data-copy-record/:page?',
  name: 'RedisDBDataCopyRecord',
  meta: {
    navName: t('数据复制记录'),
  },
  component: () => import('@views/db-manage/redis/db-data-copy-record/Index.vue'),
};

const redisVersionUpgradeRoute = createRouteItem(TicketTypes.REDIS_VERSION_UPDATE_ONLINE, t('版本升级'));

const redisWebconsoleRoute = {
  path: 'webconsole',
  name: 'RedisWebconsole',
  meta: {
    navName: 'Webconsole',
  },
  component: () => import('@views/db-manage/redis/webconsole/Index.vue'),
};

const redisQueryAccessSourceRoute = {
  path: 'query-access-source',
  name: 'RedisQueryAccessSource',
  meta: {
    navName: t('查询访问来源'),
  },
  component: () => import('@views/db-manage/redis/query-access-source/Index.vue'),
};

const redisKeyExtractRoute = createRouteItem(TicketTypes.REDIS_KEYS_EXTRACT, t('Key 操作'));
const redisKeyDeleteRoute = createRouteItem(TicketTypes.REDIS_KEYS_DELETE, t('Key 操作'));
const redisBackupRoute = createRouteItem(TicketTypes.REDIS_BACKUP, t('备份'));
const redisPurgeRoute = createRouteItem(TicketTypes.REDIS_PURGE, t('清档'));
const redisHotKeyAnalysisRoute = createRouteItem(TicketTypes.REDIS_HOT_KEY_ANALYSIS, t('热 Key 分析'));
const redisMemoryAnalysisRoute = createRouteItem(TicketTypes.REDIS_KEYSTAT, t('内存分析'));

const redisHotKeyAnalysisListRoute = {
  path: 'hot-key-analysis-list',
  name: 'RedisHotKeyAnalysisList',
  meta: {
    navName: t('热 Key 分析报告'),
  },
  component: () => import('@views/db-manage/redis/hot-key-analysis-list/Index.vue'),
};

const redisMemoryAnalysisListRoute = {
  path: 'memory-analysis-list',
  name: 'RedisMemoryAnalysisList',
  meta: {
    navName: t('内存分析报告'),
  },
  component: () => import('@views/db-manage/redis/memory-analysis-list/Index.vue'),
};

const toolboxDbConsoleRouteMap = {
  'redis.toolbox.backup': redisBackupRoute,
  'redis.toolbox.capacityChange': redisCapacityChangeRoute,
  'redis.toolbox.clusterMigrate': redisClusterMigrateRoute,
  'redis.toolbox.clusterReinstallDbmon': redisClusterReInstallDbmonRoute,
  'redis.toolbox.clusterShardChange': redisClusterShardUpdateRoute,
  'redis.toolbox.clusterTypeChange': redisClusterTypeUpdateRoute,
  'redis.toolbox.dataCopy': redisDBDataCopyRoute,
  'redis.toolbox.dataCopyRecord': redisDBDataCopyRecordRoute,
  'redis.toolbox.dbReplace': redisDBReplaceRoute,
  'redis.toolbox.hotKeyAnalysis': redisHotKeyAnalysisRoute,
  'redis.toolbox.hotKeyAnalysisList': redisHotKeyAnalysisListRoute,
  'redis.toolbox.installModule': redisInstallModuleRoute,
  'redis.toolbox.keyDelete': redisKeyDeleteRoute,
  'redis.toolbox.keyExtract': redisKeyExtractRoute,
  'redis.toolbox.masterSlaveSwap': redisMasterFailoverRoute,
  'redis.toolbox.memoryAnalysis': redisMemoryAnalysisRoute,
  'redis.toolbox.memoryAnalysisList': redisMemoryAnalysisListRoute,
  'redis.toolbox.proxyScaleDown': redisProxyScaleDownRoute,
  'redis.toolbox.proxyScaleUp': redisProxyScaleUpRoute,
  'redis.toolbox.purge': redisPurgeRoute,
  'redis.toolbox.queryAccessSource': redisQueryAccessSourceRoute,
  'redis.toolbox.recoverFromInstance': redisClusterRollbackDataCopyRoute,
  'redis.toolbox.rollback': redisDataStructureRoute,
  'redis.toolbox.rollbackRecord': redisStructureInstanceRoute,
  'redis.toolbox.shardAdd': redisShardAddRoute,
  'redis.toolbox.shardReduce': redisShardReduceRoute,
  'redis.toolbox.singleMigrate': redisSingleMigrateRoute,
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
    children: [] as RouteRecordRaw[],
  },
  createRouteItem(TicketTypes.REDIS_DATACOPY_CHECK_REPAIR, t('数据校验修复')),
];

const redisInstanceListRoute = {
  path: 'instance-list',
  name: 'DatabaseRedisInstanceList',
  meta: {
    navName: t('Redis 集群实例视图'),
  },
  component: () => import('@views/db-manage/redis/instance-list/Index.vue'),
};

const redisHaInstanceListRoute = {
  path: 'instance-ha-list',
  name: 'DatabaseRedisHaInstanceList',
  meta: {
    navName: t('Redis 主从实例视图'),
  },
  component: () => import('@views/db-manage/redis/instance-ha-list/Index.vue'),
};

const redisDatabaseHaList = {
  path: 'cluster-ha',
  name: 'DatabaseRedisHa',
  meta: {
    navName: t('Redis 主从管理'),
  },
  redirect: {
    name: 'DatabaseRedisHaList',
  },
  component: () => import('@views/db-manage/redis/Index.vue'),
  children: [
    {
      path: 'list/:clusterId?',
      name: 'DatabaseRedisHaList',
      meta: {
        navName: t('Redis 主从管理'),
      },
      component: () => import('@views/db-manage/redis/cluster-ha-list/Index.vue'),
    },
    {
      path: 'detail/:clusterId',
      name: 'redisClusterHaDetail',
      meta: {
        fullscreen: true,
        navName: t('Redis_主从集群详情'),
      },
      component: () => import('@views/db-manage/redis/cluster-ha-detail/Index.vue'),
    },
  ],
};

const routes: RouteRecordRaw[] = [
  {
    path: 'redis',
    name: 'RedisManage',
    meta: {
      dbType: DBTypes.REDIS,
      navName: t('Redis_集群管理'),
    },
    redirect: {
      name: 'DatabaseRedisList',
    },
    component: () => import('@views/db-manage/redis/Index.vue'),
    children: [
      {
        path: 'cluster',
        name: 'redisCluster',
        meta: {
          navName: t('Redis_集群管理'),
        },
        redirect: {
          name: 'DatabaseRedisList',
        },
        component: () => import('@views/db-manage/redis/Index.vue'),
        children: [
          {
            path: 'list/:clusterId?',
            name: 'DatabaseRedisList',
            meta: {
              navName: t('Redis_集群管理'),
            },
            component: () => import('@views/db-manage/redis/cluster-list/Index.vue'),
          },
          {
            path: 'detail/:clusterId',
            name: 'redisClusterDetail',
            meta: {
              fullscreen: true,
              navName: t('Redis_集群详情'),
            },
            component: () => import('@views/db-manage/redis/cluster-detail/Index.vue'),
          },
        ],
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
      toolboxRoutes[0].redirect!.name = TicketTypes.REDIS_CLUSTER_ADD_SLAVE;
    }
    routes[0].children?.push(...toolboxRoutes);
  }

  return routes;
}
