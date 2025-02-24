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

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    children: [
      {
        component: () => import('@views/db-manage/sqlserver/ha-cluster-list/Index.vue'),
        meta: {
          fullscreen: true,
          navName: t('SQLServer主从集群管理'),
        },
        name: 'SqlServerHaClusterList',
        path: 'ha-cluster-list',
      },
      {
        component: () => import('@views/db-manage/sqlserver/ha-instance-list/Index.vue'),
        meta: {
          fullscreen: true,
          navName: t('【SQLServer 主从集群】实例视图'),
        },
        name: 'SqlServerHaInstanceList',
        path: 'ha-instance-list',
      },
      {
        component: () => import('@views/db-manage/sqlserver/single-cluster-list/Index.vue'),
        meta: {
          fullscreen: true,
          navName: t('SQLServer单节点集群管理'),
        },
        name: 'SqlServerSingle',
        path: 'single-cluster-list',
      },
      {
        component: () => import('@views/db-manage/sqlserver/permission/Index.vue'),
        meta: {
          navName: t('【SQLServer】授权规则'),
        },
        name: 'SqlServerPermissionRules',
        path: 'permission-rules',
      },
    ],
    component: () => import('@views/db-manage/sqlserver/Index.vue'),
    meta: {
      navName: t('SQlServer_工具箱'),
    },
    name: 'SqlServerManage',
    path: 'sqlserver',
    redirect: {
      name: 'SqlServerSingle',
    },
  },
];

const toolboxRouters: RouteRecordRaw[] = [
  {
    children: [
      {
        component: () => import('@views/db-manage/sqlserver/sql-execute/index.vue'),
        meta: {
          navName: t('变更SQL执行'),
        },
        name: 'sqlServerExecute',
        path: 'sql-execute/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/db-rename/Index.vue'),
        meta: {
          navName: t('DB重命名'),
        },
        name: 'sqlServerDBRename',
        path: 'db-rename/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/slave-rebuild/index.vue'),
        meta: {
          navName: t('重建从库'),
        },
        name: 'sqlServerSlaveRebuild',
        path: 'slave-rebuild/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/slave-add/index.vue'),
        meta: {
          navName: t('添加从库'),
        },
        name: 'sqlServerSlaveAdd',
        path: 'slave-add/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/master-slave-swap/index.vue'),
        meta: {
          navName: t('主从互切'),
        },
        name: 'sqlServerMasterSlaveSwap',
        path: 'master-slave-swap/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/master-failover/index.vue'),
        meta: {
          navName: t('主库故障切换'),
        },
        name: 'sqlServerMasterFailover',
        path: 'master-failover/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/db-clear/Index.vue'),
        meta: {
          navName: t('清档'),
        },
        name: 'sqlServerDBClear',
        path: 'db-clear/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/rollback/Index.vue'),
        meta: {
          navName: t('定点回档'),
        },
        name: 'sqlServerDBRollback',
        path: 'rollback/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/db-backup/Index.vue'),
        meta: {
          navName: t('数据库备份'),
        },
        name: 'SqlServerDbBackup',
        path: 'db-backup/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/data-migrate/Index.vue'),
        meta: {
          navName: t('数据迁移'),
        },
        name: 'sqlServerDataMigrate',
        path: 'data-migrate/:page?',
      },
      {
        component: () => import('@views/db-manage/sqlserver/data-migrate-record/Index.vue'),
        meta: {
          navName: t('数据迁移'),
        },
        name: 'sqlServerDataMigrateRecord',
        path: 'data-migrate-record',
      },
    ],
    component: () => import('@views/db-manage/sqlserver/toolbox/Index.vue'),
    meta: {
      fullscreen: true,
      navName: t('SQlServer_工具箱'),
    },
    name: 'sqlserverToolbox',
    path: 'toolbox',
    redirect: {
      name: 'sqlServerExecute',
    },
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
