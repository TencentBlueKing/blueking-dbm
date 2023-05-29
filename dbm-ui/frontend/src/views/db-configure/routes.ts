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
    name: 'DatabaseConfig',
    path: 'config/:clusterType?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('数据库配置'),
      isMenu: true,
    },
    component: () => import('@views/db-configure/business/index.vue'),
  }, {
    name: 'DatabaseConfigDetails',
    path: 'config-details/:clusterType/:version/:confType/:treeId/:parentId?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('配置详情'),
      activeMenu: 'DatabaseConfig',
    },
    props: true,
    component: () => import('@views/db-configure/business/biz/ConfigDetails.vue'),
  }, {
    name: 'DatabaseConfigEdit',
    path: 'config-edit/:clusterType/:version/:confType/:treeId/:parentId?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('配置编辑'),
      activeMenu: 'DatabaseConfig',
    },
    props: true,
    component: () => import('@views/db-configure/business/ConfigEdit.vue'),
  }, {
    name: 'DatabaseConfigBind',
    path: 'config-bind/:clusterType/:moduleId',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('绑定模块'),
      activeMenu: 'DatabaseConfig',
    },
    component: () => import('@views/db-configure/business/ConfigBind.vue'),
  }, {
    name: 'PlatConf',
    path: 'configuration/:clusterType?',
    meta: {
      routeParentName: MainViewRouteNames.Platform,
      navName: t('数据库配置'),
      isMenu: true,
    },
    component: () => import('@views/db-configure/platform/index.vue'),
  }, {
    name: 'PlatConfEdit',
    path: 'configuration-edit/:clusterType/:version/:confType',
    meta: {
      routeParentName: MainViewRouteNames.Platform,
      navName: t('编辑平台配置'),
      activeMenu: 'PlatConf',
    },
    props: true,
    component: () => import('@views/db-configure/platform/ConfigureEdit.vue'),
  }, {
    name: 'PlatConfDetails',
    path: 'configuration-details/:clusterType/:version/:confType',
    meta: {
      routeParentName: MainViewRouteNames.Platform,
      navName: t('配置详情'),
      activeMenu: 'PlatConf',
    },
    props: true,
    component: () => import('@views/db-configure/platform/ConfigureDetails.vue'),
  },
];

export default routes;
