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
        component: () => import('@views/db-configure/platform/List.vue'),
        meta: {
          fullscreen: true,
          navName: t('数据库配置'),
        },
        name: 'PlatformDbConfigureList',
        path: 'list/:clusterType?',
      },
      {
        component: () => import('@views/db-configure/platform/Edit.vue'),
        meta: {
          navName: t('编辑平台配置'),
          // fullscreen: true,
        },
        name: 'PlatformDbConfigureEdit',
        path: 'edit/:clusterType/:version/:confType',
      },
      {
        component: () => import('@views/db-configure/platform/Detail.vue'),
        meta: {
          fullscreen: true,
          navName: t('配置详情'),
        },
        name: 'PlatformDbConfigureDetail',
        path: 'detail/:clusterType/:version/:confType',
      },
    ],
    component: () => import('@views/platform-db-configure/Index.vue'),
    meta: {
      navName: t('数据库配置'),
    },
    name: 'PlatformDbConfigure',
    path: 'platform-db-configure',
    redirect: {
      name: 'PlatformDbConfigureList',
    },
  },
];

export default function getRoutes() {
  return checkDbConsole('globalConfigManage.dbConfig') ? routes : [];
}
