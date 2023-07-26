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

import { TicketTypes } from '@common/const';

import { MainViewRouteNames } from '@views/main-views/common/const';

import { t } from '@locales/index';

const renderRoutes: RouteRecordRaw[] = [
  {
    name: 'SelfServiceApplySingle',
    path: 'apply/spider',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('申请MySQL单节点部署'),
      activeMenu: 'SelfServiceApply',
    },
    props: {
      type: TicketTypes.MYSQL_SINGLE_APPLY,
    },
    component: () => import('@views/mysql/apply/ApplyMySQL.vue'),
  },
  {
    path: 'spider-manage',
    name: 'SpiderManage',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('Spider_集群管理'),
      isMenu: true,
    },
    redirect: {
      name: 'spiderToolbox',
    },
    component: () => import('@views/spiderss-manage/Index.vue'),
    children: [
      {
        path: 'toolbox',
        name: 'spiderToolbox',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('Spider_工具箱'),
          isMenu: true,
        },
        component: () => import('@views/spiderss-manage/toolbox/Index.vue'),
        children: [
          {
            path: 'sql-execute',
            name: 'spiderSqlExecute',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('SQL变更执行'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/sql-execute/Index.vue'),
          },
          {
            path: 'db-rename',
            name: 'spiderDbRename',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('DB 重命名'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/db-rename/Index.vue'),
          },
          {
            path: 'master-slave-swap',
            name: 'spiderMasterSlaveSwap',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('主从互切'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/master-slave-swap/Index.vue'),
          },
          {
            path: 'master-failover',
            name: 'spiderMasterFailover',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('主库故障切换'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/master-failover/Index.vue'),
          },
          {
            path: 'flashback',
            name: 'spiderFlashback',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('闪回'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/flashback/Index.vue'),
          },
          {
            path: 'rollback',
            name: 'spiderRollback',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('定点构造'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/rollback/Index.vue'),
          },
          {
            path: 'db-table-backup',
            name: 'spiderDbTableBackup',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('库表备份'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/db-table-backup/Index.vue'),
          },
          {
            path: 'db-backup',
            name: 'spiderDbBackup',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('全库备份'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/db-backup/Index.vue'),
          },
          {
            path: 'db-clear',
            name: 'spiderDbClear',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('清档'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/db-clear/Index.vue'),
          },
          {
            path: 'checksum',
            name: 'spiderChecksum',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('数据校验修复'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/checksum/Index.vue'),
          },
          {
            path: 'add-mnt',
            name: 'spiderAddMnt',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('添加运维节点'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/add-mnt/Index.vue'),
          },
          {
            path: 'whitelist',
            name: 'spiderWhitelist',
            meta: {
              routeParentName: MainViewRouteNames.Database,
              navName: t('授权白名单'),
              isMenu: true,
            },
            component: () => import('@views/spiderss-manage/whitelist/pages/Index.vue'),
          },
        ],
      },
    ],
  },
];

export default function getRoutes() {
  return renderRoutes;
}
