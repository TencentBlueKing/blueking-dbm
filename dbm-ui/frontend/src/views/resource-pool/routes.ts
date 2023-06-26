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
    name: 'resourcePoolManage',
    path: 'resource-pool',
    component: () => import('@views/resource-pool/Index.vue'),
    redirect: {
      name: 'resourcePoolList',
    },
    meta: {
      routeParentName: MainViewRouteNames.Platform,
    },
    children: [
      {
        name: 'resourcePoolList',
        path: 'list',
        meta: {
          routeParentName: MainViewRouteNames.Platform,
          navName: t('DB 资源池'),
          isMenu: true,
          activeMenu: 'resourcePoolManage',
        },
        component: () => import('@views/resource-pool/list/Index.vue'),
      },
      {
        name: 'resourcePoolOperationRecord',
        path: 'record',
        meta: {
          routeParentName: MainViewRouteNames.Platform,
          navName: t('操作记录'),
          activeMenu: 'resourcePoolManage',
        },
        component: () => import('@views/resource-pool/record/Index.vue'),
      },
    ],
  },
];

export default routes;
