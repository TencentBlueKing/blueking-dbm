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

const bizResourceTagRoute = {
  path: 'resource',
  name: 'BizResourceTag',
  meta: {
    navName: t('资源标签'),
  },
  component: () => import('@/views/tag-manage/resource/Index.vue'),
};

const bizClusterTagRoute = {
  path: 'cluster',
  name: 'businessClusterTag',
  meta: {
    navName: t('集群标签管理'),
  },
  component: () => import('@/views/tag-manage/cluster/Index.vue'),
};

export default function getRoutes() {
  const routes: RouteRecordRaw[] = [
    {
      path: 'tag-manage',
      name: 'TagManage',
      component: () => import('@views/tag-manage/Index.vue'),
      children: [],
    },
  ];
  if (checkDbConsole('bizConfigManage.businessResourceTag')) {
    routes[0].children!.push(bizResourceTagRoute);
  }
  if (checkDbConsole('bizConfigManage.businessClusterTag')) {
    routes[0].children!.push(bizClusterTagRoute);
  }
  return routes;
}
