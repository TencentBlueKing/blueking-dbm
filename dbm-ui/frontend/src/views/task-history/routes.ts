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

import { registerBusinessModule, registerModule } from '@router';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

export default function getRoutes() {
  registerModule([
    {
      name: 'platformTaskManage',
      path: 'platform-task',
      component: () => import('@views/task-history/Index.vue'),
      meta: {
        navName: t('历史任务'),
      },
      redirect: {
        name: 'platformTaskHistoryList',
      },
      children: [
        {
          name: 'platformTaskHistoryList',
          path: 'list',
          meta: {
            navName: t('历史任务'),
          },
          component: () => import('@views/task-history/list/Index.vue'),
        },
        {
          name: 'platformTaskHistoryDetail',
          path: 'detail/:root_id',
          meta: {
            navName: t('任务详情'),
            fullscreen: true,
          },
          component: () => import('@views/task-history/detail/Index.vue'),
        },
      ],
    },
  ]);

  if (checkDbConsole('databaseManage.missionManage')) {
    registerBusinessModule([
      {
        name: 'taskHistory',
        path: 'task-history',
        component: () => import('@views/task-history/Index.vue'),
        meta: {
          navName: t('历史任务'),
        },
        redirect: {
          name: 'taskHistoryList',
        },
        children: [
          {
            name: 'taskHistoryList',
            path: 'list',
            meta: {
              navName: t('历史任务'),
            },
            component: () => import('@views/task-history/list/Index.vue'),
          },
          {
            name: 'taskHistoryDetail',
            path: 'detail/:root_id',
            meta: {
              navName: t('任务详情'),
              fullscreen: true,
            },
            component: () => import('@views/task-history/detail/Index.vue'),
          },
        ],
      },
    ]);
  }
}
