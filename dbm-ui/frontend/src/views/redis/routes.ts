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
    path: 'redis',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('Redis_集群管理'),
      isMenu: true,
    },
    component: () => import('@views/redis/list/List.vue'),
  }, {
    name: 'DatabaseRedisDetails',
    path: 'redis/:id/details',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('Redis集群详情'),
      activeMenu: 'DatabaseRedis',
    },
    component: () => import('@views/redis/details/Details.vue'),
  },
];

export default routes;
