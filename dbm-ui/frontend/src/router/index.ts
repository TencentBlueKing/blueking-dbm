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

import {
  useGlobalBizs,
  useMainViewStore,
} from '@stores';

import getRouters from '@views/main-views/routes';

import { routerInterceptor } from './routerInterceptor';

let router: Router;

export default async () => {
  const routers = await getRouters();

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
      ...routers,
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
