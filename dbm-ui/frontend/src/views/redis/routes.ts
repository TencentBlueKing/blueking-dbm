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

import type { RedisFunctions } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

export const redisToolboxChildrenRoutes: RouteRecordRaw[] = [
  {
    name: 'RedisCapacityChange',
    path: 'capacity-change/:page?',
    meta: {
      navName: t('集群容量变更'),
    },
    component: () => import('@views/redis/capacity-change/Index.vue'),
  },
  {
    name: 'RedisProxyScaleUp',
    path: 'proxy-scale-up/:page?',
    meta: {
      navName: t('扩容接入层'),
    },
    component: () => import('@views/redis/proxy-scale-up/Index.vue'),
  },
  {
    name: 'RedisProxyScaleDown',
    path: 'proxy-scale-down/:page?',
    meta: {
      navName: t('缩容接入层'),
    },
    component: () => import('@views/redis/proxy-scale-down/Index.vue'),
  },
  {
    name: 'RedisDBCreateSlave',
    path: 'db-create-slave/:page?',
    meta: {
      navName: t('重建从库'),
    },
    component: () => import('@views/redis/db-create-slave/Index.vue'),
  },
  {
    name: 'RedisMasterFailover',
    path: 'master-failover/:page?',
    meta: {
      navName: t('主从切换'),
    },
    component: () => import('@views/redis/master-failover/Index.vue'),
  },
  {
    name: 'RedisDBReplace',
    path: 'db-replace/:page?',
    meta: {
      navName: t('整机替换'),
    },
    component: () => import('@views/redis/db-replace/Index.vue'),
  },
  {
    name: 'RedisClusterShardUpdate',
    path: 'cluster-shard-update/:page?',
    meta: {
      navName: t('集群分片变更'),
    },
    component: () => import('@views/redis/cluster-shard-update/Index.vue'),
  },
  {
    name: 'RedisClusterTypeUpdate',
    path: 'cluster-type-update/:page?',
    meta: {
      navName: t('集群类型变更'),
    },
    component: () => import('@views/redis/cluster-type-update/Index.vue'),
  },
  {
    name: 'RedisDBStructure',
    path: 'db-structure/:page?',
    meta: {
      navName: t('定点构造'),
    },
    component: () => import('@views/redis/db-structure/Index.vue'),
  },
  {
    name: 'RedisStructureInstance',
    path: 'structure-instance/:page?',
    meta: {
      navName: t('构造实例'),
    },
    component: () => import('@views/redis/structure-instance/Index.vue'),
  },
  {
    name: 'RedisRecoverFromInstance',
    path: 'recover-from-instance/:page?',
    meta: {
      navName: t('以构造实例恢复'),
    },
    component: () => import('@views/redis/recover-from-instance/Index.vue'),
  },
  {
    name: 'RedisDBDataCopy',
    path: 'db-data-copy/:page?',
    meta: {
      navName: t('数据复制'),
    },
    component: () => import('@views/redis/db-data-copy/Index.vue'),
  },
  {
    name: 'RedisDBDataCopyRecord',
    path: 'db-data-copy-record/:page?',
    meta: {
      navName: t('数据复制记录'),
    },
    component: () => import('@views/redis/db-data-copy-record/Index.vue'),
  },
];

const toolboxRoutes: RouteRecordRaw[] = [
  {
    name: 'RedisToolbox',
    path: 'toolbox',
    redirect: {
      name: 'RedisCapacityChange',
    },
    meta: {
      navName: t('工具箱'),
      fullscreen: true,
    },
    component: () => import('@views/redis/toolbox/Index.vue'),
    children: redisToolboxChildrenRoutes,
  },
  {
    name: 'RedisToolboxDataCheckRepair',
    path: 'data-check-repair/:page?',
    meta: {
      navName: t('数据校验修复'),
    },
    component: () => import('@views/redis/data-check-repair/Index.vue'),
  },
];

const routes: RouteRecordRaw[] = [
  {
    name: 'RedisManage',
    path: 'redis-manage',
    meta: {
      navName: t('Redis_集群管理'),
    },
    redirect: {
      name: 'DatabaseRedisList',
    },
    component: () => import('@views/redis/Index.vue'),
    children: [
      {
        name: 'SelfServiceApplyRedis',
        path: 'apply',
        meta: {
          navName: t('申请Redis集群部署'),
        },
        component: () => import('@views/redis/apply/ApplyRedis.vue'),
      },
      {
        name: 'DatabaseRedisList',
        path: 'list',
        meta: {
          navName: t('Redis_集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/redis/list/Index.vue'),
      },
    ],
  },
];

export default function getRoutes(controller: Record<RedisFunctions | 'redis', boolean>) {
  if (controller.redis !== true) {
    return [];
  }

  const renderRoutes = routes.find(item => item.name === 'RedisManage');
  if (!renderRoutes) {
    return routes;
  }
  if (controller.toolbox) {
    renderRoutes.children?.push(...toolboxRoutes);
  }

  return routes;
}
