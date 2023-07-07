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
    name: 'SelfServiceMyTickets',
    path: 'my-tickets/:typeId?',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('我的服务单'),
      isMenu: true,
    },
    component: () => import('@views/tickets/my-tickets/MyTickets.vue'),
  },
  {
    name: 'MyTodos',
    path: 'my-todos',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('我的待办'),
      isMenu: true,
    },
    component: () => import('@views/tickets/my-todos/MyTodos.vue'),
  },
];

export default function getRoutes() {
  return routes;
}
