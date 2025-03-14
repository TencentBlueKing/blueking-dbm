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

import type { SqlServerFunctions } from '@services/model/function-controller/functionController';
import FunctionControllModel from '@services/model/function-controller/functionController';

import { DBTypes, TicketTypes } from '@common/const';

import { createToolboxRoute } from '@utils';

import { t } from '@locales/index';

const { createRouteItem } = createToolboxRoute(DBTypes.SQLSERVER);

const routes: RouteRecordRaw[] = [
  {
    path: 'sqlserver',
    name: 'SqlServerManage',
    meta: {
      navName: t('SQlServer_工具箱'),
    },
    redirect: {
      name: 'SqlServerSingle',
    },
    component: () => import('@views/db-manage/sqlserver/Index.vue'),
    children: [
      {
        path: 'ha-cluster-list',
        name: 'SqlServerHaClusterList',
        meta: {
          fullscreen: true,
          navName: t('SQLServer主从集群管理'),
        },
        component: () => import('@views/db-manage/sqlserver/ha-cluster-list/Index.vue'),
      },
      {
        path: 'ha-instance-list',
        name: 'SqlServerHaInstanceList',
        meta: {
          fullscreen: true,
          navName: t('【SQLServer 主从集群】实例视图'),
        },
        component: () => import('@views/db-manage/sqlserver/ha-instance-list/Index.vue'),
      },
      {
        path: 'single-cluster-list',
        name: 'SqlServerSingle',
        meta: {
          fullscreen: true,
          navName: t('SQLServer单节点集群管理'),
        },
        component: () => import('@views/db-manage/sqlserver/single-cluster-list/Index.vue'),
      },
      {
        path: 'permission-rules',
        name: 'SqlServerPermissionRules',
        meta: {
          navName: t('【SQLServer】授权规则'),
        },
        component: () => import('@views/db-manage/sqlserver/permission/Index.vue'),
      },
    ],
  },
];

const toolboxRouters: RouteRecordRaw[] = [
  {
    path: 'toolbox',
    name: 'sqlserverToolbox',
    meta: {
      fullscreen: true,
      navName: t('SQlServer_工具箱'),
    },
    redirect: {
      name: 'sqlServerExecute',
    },
    component: () => import('@views/db-manage/sqlserver/toolbox/Index.vue'),
    children: [
      {
        path: 'toolbox-result/:ticketType?/:ticketId?',
        name: 'SqlserverToolboxResult',
        component: () => import('@views/db-manage/common/toolbox-result/Index.vue'),
      },
      {
        path: 'sql-execute/:page?',
        name: 'sqlServerExecute',
        meta: {
          navName: t('变更SQL执行'),
        },
        component: () => import('@views/db-manage/sqlserver/sql-execute/index.vue'),
      },
      createRouteItem(TicketTypes.SQLSERVER_DBRENAME, t('DB重命名')),
      createRouteItem(TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE, t('重建从库')),
      createRouteItem(TicketTypes.SQLSERVER_ADD_SLAVE, t('添加从库')),
      {
        path: 'master-slave-swap/:page?',
        name: 'sqlServerMasterSlaveSwap',
        meta: {
          navName: t('主从互切'),
        },
        component: () => import('@views/db-manage/sqlserver/master-slave-swap/index.vue'),
      },
      {
        path: 'master-failover/:page?',
        name: 'sqlServerMasterFailover',
        meta: {
          navName: t('主库故障切换'),
        },
        component: () => import('@views/db-manage/sqlserver/master-failover/index.vue'),
      },
      createRouteItem(TicketTypes.SQLSERVER_CLEAR_DBS, t('清档')),
      // {
      //   path: 'rollback/:page?',
      //   name: 'sqlServerDBRollback',
      //   meta: {
      //     navName: t('定点回档'),
      //   },
      //   component: () => import('@views/db-manage/sqlserver/rollback/Index.vue'),
      // },
      createRouteItem(TicketTypes.SQLSERVER_ROLLBACK, t('定点回档')),
      createRouteItem(TicketTypes.SQLSERVER_BACKUP_DBS, t('数据库备份')),
      {
        path: 'data-migrate/:page?',
        name: 'sqlServerDataMigrate',
        meta: {
          navName: t('数据迁移'),
        },
        component: () => import('@views/db-manage/sqlserver/data-migrate/Index.vue'),
      },
      {
        path: 'data-migrate-record',
        name: 'sqlServerDataMigrateRecord',
        meta: {
          navName: t('数据迁移'),
        },
        component: () => import('@views/db-manage/sqlserver/data-migrate-record/Index.vue'),
      },
    ],
  },
];
export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<SqlServerFunctions, 'sqlserver'>('sqlserver');
  if (!controller.sqlserver) {
    return [];
  }
  if (controller.sqlserver_tool) {
    routes[0].children?.push(...toolboxRouters);
  }

  return routes;
}
