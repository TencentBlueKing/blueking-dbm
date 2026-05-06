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
      dbType: DBTypes.SQLSERVER,
      navName: t('SQlServer_工具箱'),
    },
    redirect: {
      name: 'SqlServerSingle',
    },
    component: () => import('@views/db-manage/sqlserver/Index.vue'),
    children: [
      {
        path: 'ha-cluster',
        name: 'SqlServerHaCluster',
        meta: {
          navName: t('SQLServer主从集群管理'),
        },
        redirect: {
          name: 'SqlServerHaClusterList',
        },
        component: () => import('@views/db-manage/sqlserver/Index.vue'),
        children: [
          {
            path: 'list/:clusterId?',
            name: 'SqlServerHaClusterList',
            meta: {
              navName: t('SQLServer主从集群管理'),
            },
            component: () => import('@views/db-manage/sqlserver/ha-cluster-list/Index.vue'),
          },
          {
            path: 'detail/:clusterId',
            name: 'SqlServerHaClusterDetail',
            meta: {
              fullscreen: true,
              navName: t('SQLServer主从集群详情'),
            },
            component: () => import('@views/db-manage/sqlserver/ha-cluster-detail/Index.vue'),
          },
          {
            path: 'instance-list',
            name: 'SqlServerHaInstanceList',
            meta: {
              navName: t('SQLServer 主从集群实例视图'),
            },
            component: () => import('@views/db-manage/sqlserver/ha-instance-list/Index.vue'),
          },
        ],
      },
      {
        path: 'single-cluster',
        name: 'SqlServerSingle',
        meta: {
          navName: t('SQLServer单节点集群管理'),
        },
        redirect: {
          name: 'SqlServerSingleClusterList',
        },
        component: () => import('@views/db-manage/sqlserver/Index.vue'),
        children: [
          {
            path: 'list/:clusterId?',
            name: 'SqlServerSingleClusterList',
            meta: {
              navName: t('SQLServer单节点集群管理'),
            },
            component: () => import('@views/db-manage/sqlserver/single-cluster-list/Index.vue'),
          },
          {
            path: 'detali/:clusterId',
            name: 'SqlServerSingleClusterDetail',
            meta: {
              fullscreen: true,
              navName: t('SQLServer单节点集群详情'),
            },
            component: () => import('@views/db-manage/sqlserver/single-cluster-detail/Index.vue'),
          },
        ],
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
      name: TicketTypes.SQLSERVER_IMPORT_SQLFILE,
    },
    component: () => import('@views/db-manage/sqlserver/toolbox/Index.vue'),
    children: [
      createRouteItem(TicketTypes.SQLSERVER_IMPORT_SQLFILE, t('变更SQL执行')),
      createRouteItem(TicketTypes.SQLSERVER_DBRENAME, t('DB重命名')),
      createRouteItem(TicketTypes.SQLSERVER_RESTORE_SLAVE, t('重建从库')),
      createRouteItem(TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE, t('重建从库')),
      createRouteItem(TicketTypes.SQLSERVER_ADD_SLAVE, t('添加从库')),
      createRouteItem(TicketTypes.SQLSERVER_MASTER_SLAVE_SWITCH, t('主从互切')),
      createRouteItem(TicketTypes.SQLSERVER_MASTER_FAIL_OVER, t('主库故障切换')),
      createRouteItem(TicketTypes.SQLSERVER_CLEAR_DBS, t('清档')),
      createRouteItem(TicketTypes.SQLSERVER_ROLLBACK, t('定点构造')),
      createRouteItem(TicketTypes.SQLSERVER_BACKUP_DBS, t('数据库备份')),
      createRouteItem(TicketTypes.SQLSERVER_FULL_MIGRATE, t('数据迁移')),
      createRouteItem(TicketTypes.SQLSERVER_INCR_MIGRATE, t('数据迁移')),
      createRouteItem(TicketTypes.SQLSERVER_CLUSTER_MIGRATE, t('迁移')),
      createRouteItem(TicketTypes.SQLSERVER_HOST_MIGRATE, t('迁移')),
      createRouteItem(TicketTypes.SQLSERVER_DATA_EXPORT, t('数据导出')),
      {
        path: 'data-migrate-record',
        name: 'sqlServerDataMigrateRecord',
        meta: {
          navName: t('迁移记录'),
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
