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

import FunctionControllModel from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    name: 'SqlServerManage',
    path: 'sqlserver-manage',
    children: [
      {
        name: 'SqlServerHaClusterList',
        path: 'sqlserver-ha-cluster-list',
        meta: {
          navName: t('SQLServer主从集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/sqlserver-manage/ha-cluster-list/Index.vue'),
      },
      {
        name: 'SqlServerHaInstanceList',
        path: 'sqlserver-ha-instance-list',
        meta: {
          navName: t('【SQLServer 主从集群】实例视图'),
          fullscreen: true,
        },
        component: () => import('@views/sqlserver-manage/ha-instance-list/Index.vue'),
      },
      {
        name: 'SqlServerSingle',
        path: 'sqlserver-single',
        meta: {
          navName: t('SQLServer单节点集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/sqlserver-manage/single-cluster/Index.vue'),
      },
      {
        name: 'SqlServerPermissionRules',
        path: 'permission-rules',
        meta: {
          navName: t('授权规则'),
        },
        component: () => import('@views/sqlserver-manage/permission/Index.vue'),
      },
      {
        name: 'SqlServerDbBackup',
        path: 'sqlserver-db-backup/:page?',
        meta: {
          navName: t('数据库备份'),
        },
        component: () => import('@views/sqlserver-manage/db-backup/Index.vue'),
      },
    ],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  if (funControllerData.sqlserver && !funControllerData.sqlserver.is_enabled) {
    return [];
  }
  return routes;
}
