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
    children: [
      {
        component: () => import('@views/deployment-plan/list/Index.vue'),
        meta: {
          navName: t('部署方案'),
        },
        name: 'deploymentPlanList',
        path: 'list',
      },
    ],
    component: () => import('@views/deployment-plan/Index.vue'),
    meta: {
      navName: t('部署方案'),
    },
    name: 'deploymentPlanManage',
    path: 'deployment-plan',
    redirect: {
      name: 'deploymentPlanList',
    },
  },
];

export default routes;
