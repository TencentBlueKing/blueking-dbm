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

import { MainViewRouteNames } from '@views/main-views/common/const';

import { t } from '@locales/index';

export const redisToolboxChildrenRoutes: RouteRecordRaw[] = [
  {
    name: 'RedisCapacityChange',
    path: '/database/:bizId(\\d+)/redis-toolbox/capacity-change/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('集群容量变更'),
      submenuId: 'manage',
      isMenu: true,
    },
    component: () => import('@views/redis/capacity-change/Index.vue'),
  },
  {
    name: 'RedisProxyScaleUp',
    path: '/database/:bizId(\\d+)/redis-toolbox/proxy-scale-up/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('扩容接入层'),
      submenuId: 'manage',
      isMenu: true,
    },
    component: () => import('@views/redis/proxy-scale-up/Index.vue'),
  },
  {
    name: 'RedisProxyScaleDown',
    path: '/database/:bizId(\\d+)/redis-toolbox/proxy-scale-down/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('缩容接入层'),
      submenuId: 'manage',
      isMenu: true,
    },
    component: () => import('@views/redis/proxy-scale-down/Index.vue'),
  },
  {
    name: 'RedisDBCreateSlave',
    path: '/database/:bizId(\\d+)/redis-toolbox/db-create-slave/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('新建从库'),
      submenuId: 'manage',
      isMenu: true,
    },
    component: () => import('@views/redis/db-create-slave/Index.vue'),
  },
  {
    name: 'RedisMasterFailover',
    path: '/database/:bizId(\\d+)/redis-toolbox/master-failover/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('主故障切换'),
      submenuId: 'manage',
      isMenu: true,
    },
    component: () => import('@views/redis/master-failover/Index.vue'),
  },
  {
    name: 'RedisDBReplace',
    path: '/database/:bizId(\\d+)/redis-toolbox/db-replace/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('整机替换'),
      submenuId: 'manage',
      isMenu: true,
    },
    component: () => import('@views/redis/db-replace/Index.vue'),
  },
  {
    name: 'RedisClusterShardUpdate',
    path: '/database/:bizId(\\d+)/redis-toolbox/cluster-shard-update/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('集群分片变更'),
      submenuId: 'manage',
      isMenu: true,
    },
    component: () => import('@views/redis/cluster-shard-update/Index.vue'),
  },
  {
    name: 'RedisClusterTypeUpdate',
    path: '/database/:bizId(\\d+)/redis-toolbox/cluster-type-update/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('集群类型变更'),
      submenuId: 'manage',
      isMenu: true,
    },
    component: () => import('@views/redis/cluster-type-update/Index.vue'),
  },
  {
    name: 'RedisDBStructure',
    path: '/database/:bizId(\\d+)/redis-toolbox/db-structure/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('定点构造'),
      submenuId: 'struct',
      isMenu: true,
    },
    component: () => import('@views/redis/db-structure/Index.vue'),
  },
  {
    name: 'RedisStructureInstance',
    path: '/database/:bizId(\\d+)/redis-toolbox/structure-instance/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('构造实例'),
      submenuId: 'struct',
      isMenu: true,
    },
    component: () => import('@views/redis/structure-instance/Index.vue'),
  },
  {
    name: 'RedisRecoverFromInstance',
    path: '/database/:bizId(\\d+)/redis-toolbox/recover-from-instance/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('以构造实例恢复'),
      submenuId: 'struct',
      isMenu: true,
    },
    component: () => import('@views/redis/recover-from-instance/Index.vue'),
  },
  {
    name: 'RedisDBDataCopy',
    path: '/database/:bizId(\\d+)/redis-toolbox/db-data-copy/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('数据复制'),
      submenuId: 'dts',
      isMenu: true,
    },
    component: () => import('@views/redis/db-data-copy/Index.vue'),
  },
  {
    name: 'RedisDBDataCopyRecord',
    path: '/database/:bizId(\\d+)/redis-toolbox/db-data-copy-record/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: t('数据复制记录'),
      submenuId: 'dts',
      isMenu: true,
    },
    component: () => import('@views/redis/db-data-copy-record/Index.vue'),
  },
];

const routes: RouteRecordRaw[] = [
  {
    name: 'SelfServiceApplyRedis',
    path: 'apply/redis',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('申请Redis集群部署'),
      activeMenu: 'SelfServiceApply',
    },
    component: () => import('@views/redis/apply/ApplyRedis.vue'),
  },
  {
    name: 'DatabaseRedis',
    path: 'redis-manage',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('Redis_集群管理'),
      isMenu: true,
    },
    component: () => import('@views/redis/cluster-manage/Index.vue'),
  },
];

const toolboxRoutes: RouteRecordRaw[] = [
  {
    name: 'RedisToolbox',
    path: 'redis-toolbox',
    redirect: {
      name: 'RedisCapacityChange',
    },
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('工具箱'),
      isMenu: true,
    },
    component: () => import('@views/redis/toolbox/Index.vue'),
    children: redisToolboxChildrenRoutes,
  },
  {
    name: 'RedisToolboxDataCheckRepair',
    path: 'data-check-repair/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('数据校验修复'),
    },
    component: () => import('@views/redis/data-check-repair/Index.vue'),
  },
];

export default function getRoutes(controller: Record<RedisFunctions | 'redis', boolean>) {
  if (controller.redis !== true) return [];

  const renderRoutes: RouteRecordRaw[] = [...routes];
  if (controller.toolbox) {
    renderRoutes.push(...toolboxRoutes);
  }

  return renderRoutes;
}
