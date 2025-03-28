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
import { TicketTypes } from '@common/const';

import { t } from '@locales/index';

const createRouteItem = (ticketType: TicketTypes, navName: string) => ({
  path: `${ticketType}:page?`,
  name: `DBA_${ticketType}`,
  meta: {
    navName,
  },
  component: () => import(`@views/db-manage/redis/dba-manage/${ticketType}/Index.vue`),
});

export default function getRoutes() {
  return [
    {
      path: 'redis',
      name: 'DbaManageRedis',
      meta: {
        navName: t('Redis 工具箱'),
      },
      redirect: {
        name: `DBA_${TicketTypes.REDIS_CLUSTER_CUTOFF}`,
      },
      component: () => import('@views/db-manage/redis/dba-manage/Index.vue'),
      children: [createRouteItem(TicketTypes.REDIS_CLUSTER_CUTOFF, t('整机替换'))],
    },
  ];
}
