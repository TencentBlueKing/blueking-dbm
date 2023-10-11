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
    name: 'PlatformDbConfigure',
    path: 'platform-db-configure',
    meta: {
      routeParentName: MainViewRouteNames.Platform,
      navName: t('数据库配置'),
      isMenu: true,
    },
    redirect: {
      name: 'PlatformDbConfigureList',
    },
    component: () => import('@views/platform-db-configure/Index.vue'),
    children: [
      {
        name: 'PlatformDbConfigureList',
        path: 'list/:clusterType?',
        meta: {
          routeParentName: MainViewRouteNames.Platform,
          navName: t('数据库配置'),
          activeMenu: 'PlatformDbConfigure',
        },
        component: () => import('@views/db-configure/platform/List.vue'),
      },
      {
        name: 'PlatformDbConfigureEdit',
        path: 'edit/:clusterType/:version/:confType',
        meta: {
          routeParentName: MainViewRouteNames.Platform,
          navName: t('编辑平台配置'),
          activeMenu: 'PlatformDbConfigure',
        },
        props: true,
        component: () => import('@views/db-configure/platform/Edit.vue'),
      },
      {
        name: 'PlatformDbConfigureDetail',
        path: 'detail/:clusterType/:version/:confType',
        meta: {
          routeParentName: MainViewRouteNames.Platform,
          navName: t('配置详情'),
          activeMenu: 'PlatformDbConfigure',
        },
        props: true,
        component: () => import('@views/db-configure/platform/Detail.vue'),
      },
    ],
  },

];

export default function getRoutes() {
  return routes;
}
