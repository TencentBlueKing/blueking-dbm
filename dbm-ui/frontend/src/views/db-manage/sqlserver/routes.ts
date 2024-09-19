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
    name: 'SqlServerManage',
    path: 'sqlserver',
    meta: {
      navName: t('SQlServer_工具箱'),
    },
    redirect: {
      name: 'SqlServerSingle',
    },
    component: () => import('@views/db-manage/sqlserver/Index.vue'),
    children: [
      {
        name: 'SqlServerHaClusterList',
        path: 'ha-cluster-list',
        meta: {
          navName: t('SQLServer主从集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/sqlserver/ha-cluster-list/Index.vue'),
      },
      {
        name: 'SqlServerHaInstanceList',
        path: 'ha-instance-list',
        meta: {
          navName: t('【SQLServer 主从集群】实例视图'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/sqlserver/ha-instance-list/Index.vue'),
      },
      {
        name: 'SqlServerSingle',
        path: 'single-cluster-list',
        meta: {
          navName: t('SQLServer单节点集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/sqlserver/single-cluster/Index.vue'),
      },
      {
        name: 'SqlServerPermissionRules',
        path: 'permission-rules',
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
      navName: t('SQlServer_工具箱'),
      fullscreen: true,
    },
    redirect: {
      name: 'sqlServerExecute',
    },
    component: () => import('@views/db-manage/sqlserver/toolbox/Index.vue'),
    children: [
      {
        name: 'sqlServerExecute',
        path: 'sql-execute/:page?',
        meta: {
          navName: t('变更SQL执行'),
        },
        component: () => import('@views/db-manage/sqlserver/sql-execute/index.vue'),
      },
      {
        name: 'sqlServerDBRename',
        path: 'db-rename/:page?',
        meta: {
          navName: t('DB重命名'),
        },
        component: () => import('@views/db-manage/sqlserver/db-rename/Index.vue'),
      },
      {
        name: 'sqlServerSlaveRebuild',
        path: 'slave-rebuild/:page?',
        meta: {
          navName: t('重建从库'),
        },
        component: () => import('@views/db-manage/sqlserver/slave-rebuild/index.vue'),
      },
      {
        name: 'sqlServerSlaveAdd',
        path: 'slave-add/:page?',
        meta: {
          navName: t('添加从库'),
        },
        component: () => import('@views/db-manage/sqlserver/slave-add/index.vue'),
      },
      {
        name: 'sqlServerMasterSlaveSwap',
        path: 'master-slave-swap/:page?',
        meta: {
          navName: t('主从互切'),
        },
        component: () => import('@views/db-manage/sqlserver/master-slave-swap/index.vue'),
      },
      {
        name: 'sqlServerMasterFailover',
        path: 'master-failover/:page?',
        meta: {
          navName: t('主库故障切换'),
        },
        component: () => import('@views/db-manage/sqlserver/master-failover/index.vue'),
      },
      {
        name: 'sqlServerDBClear',
        path: 'db-clear/:page?',
        meta: {
          navName: t('清档'),
        },
        component: () => import('@views/db-manage/sqlserver/db-clear/Index.vue'),
      },
      {
        name: 'sqlServerDBRollback',
        path: 'rollback/:page?',
        meta: {
          navName: t('定点回档'),
        },
        component: () => import('@views/db-manage/sqlserver/rollback/Index.vue'),
      },
      {
        name: 'SqlServerDbBackup',
        path: 'db-backup/:page?',
        meta: {
          navName: t('数据库备份'),
        },
        component: () => import('@views/db-manage/sqlserver/db-backup/Index.vue'),
      },
      {
        name: 'sqlServerDataMigrate',
        path: 'data-migrate/:page?',
        meta: {
          navName: t('数据迁移'),
        },
        component: () => import('@views/db-manage/sqlserver/data-migrate/Index.vue'),
      },
      {
        name: 'sqlServerDataMigrateRecord',
        path: 'data-migrate-record',
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
