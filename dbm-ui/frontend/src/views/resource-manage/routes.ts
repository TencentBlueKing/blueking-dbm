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

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    name: 'resourceManage',
    path: 'resource-manage',
    component: () => import('@views/resource-manage/Index.vue'),
    redirect: {
      name: 'resourcePoolList',
    },
    children: [
      {
        name: 'resourcePoolList',
        path: 'pool',
        meta: {
          navName: t('DB 资源池'),
        },
        component: () => import('@views/resource-manage/list/Index.vue'),
      },
      {
        name: 'resourcePoolOperationRecord',
        path: 'record',
        meta: {
          navName: t('操作记录'),
        },
        component: () => import('@views/resource-manage/record/Index.vue'),
      },
      {
        name: 'resourcePoolDirtyMachines',
        path: 'dirty-machine',
        meta: {
          navName: t('污点主机处理'),
        },
        component: () => import('@views/resource-manage/dirty-machine/Index.vue'),
      },
      {
        name: 'resourceSpec',
        path: 'spec',
        meta: {
          navName: t('资源规格管理'),
        },
        component: () => import('@views/resource-manage/spec/Index.vue'),
      },
    ],
  },
];

export default function getRoutes() {
  return routes;
}
