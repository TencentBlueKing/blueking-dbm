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
    name: 'deploymentPlanManage',
    path: 'deployment-plan',
    component: () => import('@views/deployment-plan/Index.vue'),
    redirect: {
      name: 'deploymentPlanList',
    },
    meta: {
      routeParentName: MainViewRouteNames.Platform,
    },
    children: [
      {
        name: 'deploymentPlanList',
        path: 'list',
        meta: {
          routeParentName: MainViewRouteNames.Platform,
          navName: t('部署方案'),
          isMenu: true,
          activeMenu: 'deploymentPlanManage',
        },
        component: () => import('@views/deployment-plan/list/Index.vue'),
      },
    ],
  },
];

export default routes;
