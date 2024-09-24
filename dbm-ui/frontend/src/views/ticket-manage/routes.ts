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
    name: 'ticketManage',
    path: 'ticket-manage',
    component: () => import('@views/ticket-manage/Index.vue'),
    meta: {
      navName: t('单据管理'),
    },
    redirect: {
      name: 'bizTicketManage',
    },
    children: [],
  },
];

export default function getRoutes() {
  if (checkDbConsole('databaseManage.missionManage')) {
    routes[0].children.push({
      name: 'bizTicketManage',
      path: 'index',
      meta: {
        navName: t('单据'),
        fullscreen: true,
      },
      component: () => import('@views/ticket-manage/list/Index.vue'),
    });
  }

  return routes;
}
