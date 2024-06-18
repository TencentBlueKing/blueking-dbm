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

import FunctionControllModel from '@services/model/function-controller/functionController';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

const selfServiceMyTicketsRoute = {
  name: 'SelfServiceMyTickets',
  path: 'my-tickets/:typeId?',
  meta: {
    navName: t('单据'),
    fullscreen: true,
  },
  component: () => import('@views/tickets/my-tickets/Index.vue'),
};

const myTodosRoute = {
  name: 'MyTodos',
  path: 'my-todos',
  meta: {
    navName: t('我的待办'),
    fullscreen: true,
  },
  component: () => import('@views/tickets/my-todos/Index.vue'),
};

const myTodosNewRoute = {
  name: 'MyTodosNew',
  path: 'my-todos-new',
  meta: {
    navName: t('我的待办[新]'),
    fullscreen: true,
  },
  redirect: {
    name: 'MyTodosNewIndex',
  },
  children: [
    {
      name: 'MyTodosNewIndex',
      path: 'index',
      meta: {
        navName: t('我的待办[新]'),
        fullscreen: true,
      },
      component: () => import('@views/tickets/my-todos-new/Index.vue'),
    },
    {
      name: 'MyTodosDetailsNew',
      path: 'details',
      meta: {
        navName: t('我的待办[新]'),
        fullscreen: true,
      },
      component: () => import('@views/tickets/my-todos-new/Details.vue'),
    },
  ],
};

export default function getRoutes(funControllerData: FunctionControllModel) {
  const routes: RouteRecordRaw[] = [];

  if (checkDbConsole(funControllerData, 'personalWorkbench.myTickets')) {
    routes.push(selfServiceMyTicketsRoute);
  }

  if (checkDbConsole(funControllerData, 'personalWorkbench.myTodos')) {
    routes.push(myTodosRoute);
  }

  if (checkDbConsole(funControllerData, 'personalWorkbench.myTodosNew')) {
    routes.push(myTodosNewRoute);
  }

  return routes;
}
