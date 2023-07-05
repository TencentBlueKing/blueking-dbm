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

import {
  createRouter,
  createWebHistory,
  type Router,
} from 'vue-router';

import { checkAuthAllowed } from '@services/common';

import {
  useGlobalBizs,
  useMainViewStore,
} from '@stores';

import {
  databaseRoutes,
  platformRoutes,
  serviceRoutes,
} from '@views/main-views/routes';

import { routerInterceptor } from './routerInterceptor';

let router: Router;

export default async () => {
  // 注册平台管理功能
  const [{ is_allowed: isAllowed = false }] = await checkAuthAllowed({
    action_ids: ['DB_MANAGE'],
    resources: [],
  });
  const renderRouters = isAllowed ? platformRoutes : [];

  router = createRouter({
    history: createWebHistory(window.PROJECT_ENV.VITE_ROUTER_PERFIX),
    routes: [
      {
        path: '/',
        redirect: {
          name: 'SelfServiceApply',
        },
      },
      {
        path: '/:pathMatch(.*)*',
        name: '404',
        component: () => import('@views/exception/404.vue'),
      },
      ...serviceRoutes,
      ...databaseRoutes,
      ...renderRouters,
    ],
  });

  routerInterceptor(router);

  let isLoadBizs = false;
  router.beforeEach(async (to, from, next) => {
    if (!isLoadBizs) {
      const globalBizsStore = useGlobalBizs();
      await globalBizsStore.fetchBizs();
      isLoadBizs = true;
    }

    next();
  });

  router.afterEach((to, from) => {
    // 还原面包屑设置
    if (from.name !== to.name) {
      const mainViewStore = useMainViewStore();
      mainViewStore.$patch({
        breadCrumbsTitle: '',
        customBreadcrumbs: false,
        hasPadding: true,
        tags: [],
      });
    }
  });

  return router;
};

export const getRouter = () => router;
