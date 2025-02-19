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
    children: [
      {
        component: () => import('@views/db-configure/business/list/Index.vue'),
        meta: {
          fullscreen: true,
          navName: t('数据库配置'),
        },
        name: 'DbConfigureList',
        path: 'list/:clusterType?',
      },
      {
        component: () => import('@views/db-configure/business/Detail.vue'),
        meta: {
          fullscreen: true,
          navName: t('配置详情'),
        },
        name: 'DbConfigureDetail',
        path: 'detail/:clusterType/:version/:confType/:treeId/:parentId?',
        props: true,
      },
      {
        component: () => import('@views/db-configure/business/Edit.vue'),
        meta: {
          navName: t('配置编辑'),
        },
        name: 'DbConfigureEdit',
        path: 'edit/:clusterType/:version/:confType/:treeId/:parentId?',
        props: true,
      },
      {
        component: () => import('@views/db-configure/business/Bind.vue'),
        meta: {
          navName: t('绑定模块'),
        },
        name: 'DbConfigureBind',
        path: 'bind/:clusterType/:moduleId',
      },
      {
        component: () => import('@views/service-apply/create-db-module/Index.vue'),
        meta: {
          navName: t('新建模块'),
        },
        name: 'SelfServiceCreateDbModule',
        path: 'create-db-module/:type/:bk_biz_id/',
      },
      {
        component: () => import('@views/db-manage/tendb-cluster/apply/CreateModule.vue'),
        meta: {
          navName: t('新建模块'),
        },
        name: 'createSpiderModule',
        path: 'create-module/:bizId(\\d+)',
      },
      {
        component: () => import('@views/service-apply/create-db-module/SqlServerCreateDbModule.vue'),
        meta: {
          navName: t('新建模块'),
        },
        name: 'SqlServerCreateDbModule',
        path: 'sqlserver-create-db-module/:ticketType/:bizId/',
      },
    ],
    component: () => import('@views/db-configure/Index.vue'),
    meta: {
      navName: t('数据库配置'),
    },
    name: 'DbConfigure',
    path: 'db-configure',
    redirect: {
      name: 'DbConfigureList',
    },
  },
];

export default function getRoutes() {
  return checkDbConsole('bizConfigManage.dbConfigure') ? routes : [];
}
