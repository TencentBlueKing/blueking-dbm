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

const modules = import.meta.glob<{ default: () => RouteRecordRaw[] }>('./*/routes.ts', { eager: true });

export default function getRoutes() {
  const children = Object.values(modules).reduce((result, item) => {
    const routes = item.default();
    if (Array.isArray(routes) && routes.length > 0) {
      result.push(routes[0]);
    }
    return result;
  }, [] as RouteRecordRaw[]);

  const routes = [
    {
      name: 'DbManage',
      path: 'db-manage',
      meta: {
        navName: t('数据库管理'),
      },
      component: () => import('@views/db-manage/Index.vue'),
      children,
    },
  ];

  console.log('routes = ', routes);

  return routes;
}
