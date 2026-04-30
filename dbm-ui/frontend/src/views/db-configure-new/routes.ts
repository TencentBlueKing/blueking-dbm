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

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    path: 'db-configure',
    name: 'DbConfigure',
    meta: {
      navName: t('数据库配置'),
    },
    redirect: {
      name: 'DbConfigureList',
    },
    component: () => import('@views/db-configure-new/Index.vue'),
    children: [
      {
        path: 'list/:clusterType?',
        name: 'DbConfigureList',
        meta: {
          fullscreen: true,
          navName: t('数据库配置'),
        },
        component: () => import('@views/db-configure-new/business/list/Index.vue'),
      },
      {
        path: 'detail/:clusterType/:version/:confType/:treeId/:parentId?',
        name: 'DbConfigureDetail',
        meta: {
          fullscreen: true,
          navName: '',
        },
        props: true,
        component: () => import('@views/db-configure-new/business/detail/Index.vue'),
      },
      {
        path: 'create-db-module/:type/:bk_biz_id/',
        name: 'SelfServiceCreateDbModule',
        meta: {
          navName: t('新建模块'),
        },
        component: () => import('@views/db-configure-new/business/create-module/Index.vue'),
      },
      {
        path: 'create-module/:bizId(\\d+)',
        name: 'createSpiderModule',
        meta: {
          navName: t('新建模块'),
        },
        component: () => import('@views/db-configure-new/business/create-module/TendbCluster.vue'),
      },
      {
        path: 'sqlserver-create-db-module/:ticketType/:bizId/',
        name: 'SqlServerCreateDbModule',
        meta: {
          navName: t('新建模块'),
        },
        component: () => import('@views/db-configure-new/business/create-module/SqlServer.vue'),
      },
      {
        path: 'create-db-module/:type/:bk_biz_id/',
        name: 'SelfServiceCloneDbModule',
        meta: {
          navName: t('克隆模块'),
        },
        component: () => import('@views/db-configure-new/business/create-module/Index.vue'),
      },
      {
        path: 'create-module/:bizId(\\d+)',
        name: 'cloneSpiderModule',
        meta: {
          navName: t('克隆模块'),
        },
        component: () => import('@views/db-configure-new/business/create-module/TendbCluster.vue'),
      },
      {
        path: 'sqlserver-create-db-module/:ticketType/:bizId/',
        name: 'SqlServerCloneDbModule',
        meta: {
          navName: t('克隆模块'),
        },
        component: () => import('@views/db-configure-new/business/create-module/SqlServer.vue'),
      },
    ],
  },
];

export default function getRoutes() {
  return checkDbConsole('bizConfigManage.dbConfigure') ? routes : [];
}
