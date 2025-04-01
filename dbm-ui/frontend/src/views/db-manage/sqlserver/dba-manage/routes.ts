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
import { t } from '@locales/index';

export default function getRoutes() {
  return [
    {
      path: 'sqlserver',
      name: 'DbaManageSQLServer',
      meta: {
        navName: t('SQLServer 工具箱'),
      },
      redirect: {
        name: 'DbaManageSQLServerWebQuery',
      },
      component: () => import('@views/db-manage/sqlserver/dba-manage/Index.vue'),
      children: [
        {
          path: 'web-query',
          name: 'DbaManageSQLServerWebQuery',
          meta: {
            navName: t('管理控制台'),
          },
          component: () => import('@views/db-manage/sqlserver/dba-manage/web-query/Index.vue'),
        },
      ],
    },
  ];
}
