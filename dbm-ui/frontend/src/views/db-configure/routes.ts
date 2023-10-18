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
    name: 'DbConfigure',
    path: 'db-configure',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('数据库配置'),
      isMenu: true,
    },
    redirect: {
      name: 'DbConfigureList',
    },
    component: () => import('@views/db-configure/Index.vue'),
    children: [
      {
        name: 'DbConfigureList',
        path: 'list/:clusterType?',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('数据库配置'),
          activeMenu: 'DbConfigure',
        },
        component: () => import('@views/db-configure/business/list/Index.vue'),
      },
      {
        name: 'DbConfigureDetail',
        path: 'detail/:clusterType/:version/:confType/:treeId/:parentId?',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('配置详情'),
          activeMenu: 'DbConfigure',
        },
        props: true,
        component: () => import('@views/db-configure/business/Detail.vue'),
      },
      {
        name: 'DbConfigureEdit',
        path: 'edit/:clusterType/:version/:confType/:treeId/:parentId?',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('配置编辑'),
          activeMenu: 'DbConfigure',
        },
        props: true,
        component: () => import('@views/db-configure/business/Edit.vue'),
      },
      {
        name: 'DbConfigureBind',
        path: 'bind/:clusterType/:moduleId',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('绑定模块'),
          activeMenu: 'DbConfigure',
        },
        component: () => import('@views/db-configure/business/Bind.vue'),
      },
    ],
  },
];

export default function getRoutes() {
  return routes;
}
