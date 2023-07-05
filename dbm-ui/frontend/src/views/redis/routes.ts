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

import { MainViewRouteNames } from '@views/main-views/common/const';

import { t } from '@locales/index';

/**
 * 工具箱 routes
 */
export const toolboxRoutes: RouteRecordRaw[] = [
  {
    name: 'RedisCapacityChange',
    path: '/database/:bizId(\\d+)/redis-toolbox/capacity-change/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: '集群容量变更', // TODO: I18n
      submenuId: 'redis',
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
      navName: '扩容接入层', // TODO: I18n
      submenuId: 'redis',
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
      navName: '缩容接入层', // TODO: I18n
      submenuId: 'redis',
      isMenu: true,
    },
    component: () => import('@views/redis/proxy-scale-down/Index.vue'),
  },
  {
    name: 'RedisDBReplace',
    path: '/database/:bizId(\\d+)/redis-toolbox/db-replace/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'RedisToolbox',
      navName: '整机替换', // TODO: I18n
      submenuId: 'redis',
      isMenu: true,
    },
    component: () => import('@views/redis/db-replace/Index.vue'),
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
  {
    name: 'RedisToolbox',
    path: 'redis-toolbox',
    redirect: {
      name: 'RedisDBReplace',
    },
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('工具箱'),
      isMenu: true,
    },
    component: () => import('@views/redis/toolbox/Index.vue'),
    children: toolboxRoutes,
  },
];

export default routes;
