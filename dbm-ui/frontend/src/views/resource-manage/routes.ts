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

import { registerBusinessModule, registerModule } from '@router';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

export default function getRoutes() {
  // 注册全局路由
  registerModule([
    {
      path: 'resource-manage',
      name: 'resourceManage',
      redirect: {
        name: 'resourcePool',
      },
      component: () => import('@views/resource-manage/Index.vue'),
      children: [
        checkDbConsole('resourceManage.resourceSpec') && {
          path: 'spec',
          name: 'resourceSpec',
          meta: {
            fullscreen: true,
            navName: t('资源规格管理'),
          },
          component: () => import('@views/resource-manage/spec/Index.vue'),
        },
        checkDbConsole('resourceManage.resourcePool') && {
          path: 'pool/:page?',
          name: 'resourcePool',
          meta: {
            fullscreen: true,
            navName: t('DB 资源池'),
          },
          component: () => import('@views/resource-manage/pool/global/Index.vue'),
        },
        checkDbConsole('resourceManage.faultPool') && {
          path: 'fault-pool',
          name: 'faultPool',
          meta: {
            navName: t('故障池'),
          },
          component: () => import('@views/resource-manage/fault-or-recycle-list/Index.vue'),
        },
        checkDbConsole('resourceManage.toRecyclePool') && {
          path: 'to-recycle-pool',
          name: 'toRecyclePool',
          meta: {
            navName: t('待回收池'),
          },
          component: () => import('@views/resource-manage/fault-or-recycle-list/Index.vue'),
        },
        checkDbConsole('personalWorkbench.hostTodo') && {
          path: 'host-todo/:type?/',
          name: 'resourceManageHostTodo',
          meta: {
            fullscreen: true,
            isMenu: true,
            navName: t('主机处理待办'),
          },
          component: () => import('@views/resource-manage/todo/Index.vue'),
        },
        checkDbConsole('resourceManage.allHost') && {
          path: 'all-host',
          name: 'allHost',
          meta: {
            navName: t('所有主机'),
          },
          component: () => import('@views/resource-manage/pool/all-host/Index.vue'),
        },
        checkDbConsole('resourceManage.resourceTagsManagement') && {
          path: 'resource-tag',
          name: 'resourceTagsManagement',
          meta: {
            navName: t('资源标签管理'),
          },
          component: () => import('@views/resource-manage/resource-tag/Index.vue'),
        },
        checkDbConsole('resourceManage.resourceOperationRecord') && {
          path: 'record',
          name: 'resourcePoolOperationRecord',
          meta: {
            fullscreen: true,
            navName: t('资源操作记录'),
          },
          redirect: {
            name: 'resourceFlowRecord',
          },
          children: [
            {
              path: 'flow',
              name: 'resourceFlowRecord',
              meta: {
                fullscreen: true,
                navName: t('资源操作记录'),
              },
              component: () => import('@views/resource-manage/record/Index.vue'),
            },
            {
              path: 'replenish/:page?/:id?',
              name: 'resourceReplenishRecord',
              meta: {
                fullscreen: true,
                navName: t('资源补货记录'),
              },
              component: () => import('@views/resource-manage/record/Index.vue'),
            },
          ],
        },
      ].filter((_) => _) as RouteRecordRaw[],
    },
  ]);

  // 注册业务路由
  registerBusinessModule([
    {
      path: 'resource-manage',
      name: 'BizResourceManage',
      children: [
        {
          path: 'pool/:page?',
          name: 'BizResourcePool',
          meta: {
            fullscreen: true,
            navName: t('资源池'),
          },
          component: () => import('@views/resource-manage/pool/business/Index.vue'),
        },
        checkDbConsole('bizConfigManage.businessResourceTag') && {
          path: 'resource-tag',
          name: 'BizResourceTag',
          meta: {
            navName: t('资源标签'),
          },
          component: () => import('@views/resource-manage/resource-tag/Index.vue'),
        },
        checkDbConsole('bizConfigManage.businessClusterTag') && {
          path: 'cluster-tag',
          name: 'businessClusterTag',
          meta: {
            navName: t('集群标签管理'),
          },
          component: () => import('@views/resource-manage/cluster-tag/Index.vue'),
        },
      ].filter((_) => _) as RouteRecordRaw[],
    },
  ]);
}
