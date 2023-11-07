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

import type { MySQLFunctions } from '@services/model/function-controller/functionController';

import { TicketTypes } from '@common/const';

import { MainViewRouteNames } from '@views/main-views/common/const';

import { t } from '@locales/index';

export const mysqlToolboxChildrenRouters: RouteRecordRaw[] = [
  {
    name: 'MySQLExecute',
    path: '/database/:bizId(\\d+)/mysql-toolbox/execute/:step?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('变更SQL执行'),
      submenuId: 'sql',
      isMenu: true,
    },
    component: () => import('@views/mysql/sql-execute/index.vue'),
  },
  {
    name: 'MySQLDBRename',
    path: '/database/:bizId(\\d+)/mysql-toolbox/db-rename',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('DB重命名'),
      submenuId: 'sql',
      isMenu: true,
    },
    component: () => import('@views/mysql/db-rename/index.vue'),
  },
  {
    name: 'MySQLPrivilegeCloneClient',
    path: '/database/:bizId(\\d+)/mysql-toolbox/privilege-clone-client',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('客户端权限克隆'),
      submenuId: 'privilege',
      isMenu: true,
    },
    component: () => import('@views/mysql/privilege-clone-client/index.vue'),
  },
  {
    name: 'MySQLPrivilegeCloneInst',
    path: '/database/:bizId(\\d+)/mysql-toolbox/privilege-clone-inst',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('DB实例权限克隆'),
      submenuId: 'privilege',
      isMenu: true,
    },
    component: () => import('@views/mysql/privilege-clone-inst/index.vue'),
  },
  {
    name: 'MySQLSlaveRebuild',
    path: '/database/:bizId(\\d+)/mysql-toolbox/slave-rebuild/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('重建从库'),
      submenuId: 'migrate',
      isMenu: true,
    },
    component: () => import('@views/mysql/slave-rebuild/index.vue'),
  },
  {
    name: 'MySQLSlaveAdd',
    path: '/database/:bizId(\\d+)/mysql-toolbox/slave-add',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('添加从库'),
      submenuId: 'migrate',
      isMenu: true,
    },
    component: () => import('@views/mysql/slave-add/index.vue'),
  },
  {
    name: 'MySQLMasterSlaveClone',
    path: '/database/:bizId(\\d+)/mysql-toolbox/master-slave-clone/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('克隆主从'),
      submenuId: 'migrate',
      isMenu: true,
    },
    component: () => import('@views/mysql/master-slave-clone/index.vue'),
  },
  {
    name: 'MySQLMasterSlaveSwap',
    path: '/database/:bizId(\\d+)/mysql-toolbox/master-slave-swap/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('主从互切'),
      submenuId: 'migrate',
      isMenu: true,
    },
    component: () => import('@views/mysql/master-slave-swap/index.vue'),
  },
  {
    name: 'MySQLProxyReplace',
    path: '/database/:bizId(\\d+)/mysql-toolbox/proxy-replace/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('替换Proxy'),
      submenuId: 'migrate',
      isMenu: true,
    },
    component: () => import('@views/mysql/proxy-replace/index.vue'),
  },
  {
    name: 'MySQLProxyAdd',
    path: '/database/:bizId(\\d+)/mysql-toolbox/proxy-add/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('添加Proxy'),
      submenuId: 'migrate',
      isMenu: true,
    },
    component: () => import('@views/mysql/proxy-add/index.vue'),
  },
  {
    name: 'MySQLMasterFailover',
    path: '/database/:bizId(\\d+)/mysql-toolbox/master-failover/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('主库故障切换'),
      submenuId: 'migrate',
      isMenu: true,
    },
    component: () => import('@views/mysql/master-failover/index.vue'),
  },
  {
    name: 'MySQLDBTableBackup',
    path: '/database/:bizId(\\d+)/mysql-toolbox/db-table-backup/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('库表备份'),
      submenuId: 'copy',
      isMenu: true,
    },
    component: () => import('@views/mysql/db-table-backup/index.vue'),
  },
  {
    name: 'MySQLDBBackup',
    path: '/database/:bizId(\\d+)/mysql-toolbox/db-backup/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('全库备份'),
      submenuId: 'copy',
      isMenu: true,
    },
    component: () => import('@views/mysql/db-backup/index.vue'),
  },
  {
    name: 'MySQLDBClear',
    path: '/database/:bizId(\\d+)/mysql-toolbox/db-clear',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('清档'),
      submenuId: 'data',
      isMenu: true,
    },
    component: () => import('@views/mysql/db-clear/index.vue'),
  },
  {
    name: 'MySQLDBRollback',
    path: '/database/:bizId(\\d+)/mysql-toolbox/rollback/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('定点回档'),
      submenuId: 'fileback',
      isMenu: true,
    },
    component: () => import('@views/mysql/rollback/Index.vue'),
  },
  {
    name: 'MySQLDBFlashback',
    path: '/database/:bizId(\\d+)/mysql-toolbox/flashback/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('闪回'),
      submenuId: 'fileback',
      isMenu: true,
    },
    component: () => import('@views/mysql/flashback/Index.vue'),
  },
  {
    name: 'MySQLChecksum',
    path: '/database/:bizId(\\d+)/mysql-toolbox/checksum',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      activeMenu: 'MySQLToolbox',
      navName: t('数据校验修复'),
      submenuId: 'data',
      isMenu: true,
    },
    component: () => import('@views/mysql/checksum/Index.vue'),
  },
];

const singleRoutes: RouteRecordRaw[] = [
  {
    name: 'DatabaseTendbsingle',
    path: 'single-cluster-list',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('MySQL单节点_集群管理'),
      isMenu: true,
      submenuId: 'database-tendbha-cluster',
    },
    component: () => import('@views/mysql/single-cluster-list/Index.vue'),
  },
];

const haRoutes: RouteRecordRaw[] = [
  {
    name: 'DatabaseTendbha',
    path: 'ha-cluster-list',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('MySQL高可用集群_集群管理'),
      isMenu: true,
      submenuId: 'database-tendbha-cluster',
    },
    component: () => import('@views/mysql/ha-cluster-list/Index.vue'),
  },
  {
    name: 'DatabaseTendbhaInstance',
    path: 'ha-instance-list',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('MySQL高可用集群_实例视图'),
      isMenu: true,
      submenuId: 'database-tendbha-cluster',
    },
    component: () => import('@views/mysql/ha-instance-list/Index.vue'),
  },
];

const mysqlToolboxRouters: RouteRecordRaw[] = [
  {
    name: 'MySQLToolbox',
    path: 'mysql-toolbox',
    redirect: {
      name: 'MySQLExecute',
    },
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('工具箱'),
      isMenu: true,
    },
    component: () => import('@views/mysql/toolbox/index.vue'),
    children: mysqlToolboxChildrenRouters,
  },
];

const commonRouters: RouteRecordRaw[] = [
  {
    name: 'SelfServiceApplySingle',
    path: 'apply/single',
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
    name: 'SelfServiceApplyHa',
    path: 'apply/ha',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('申请MySQL高可用部署'),
      activeMenu: 'SelfServiceApply',
    },
    props: {
      type: TicketTypes.MYSQL_HA_APPLY,
    },
    component: () => import('@views/mysql/apply/ApplyMySQL.vue'),
  },
  {
    name: 'SelfServiceCreateDbModule',
    path: 'create-db-module/:type/:bk_biz_id/',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('新建模块'),
      activeMenu: 'SelfServiceApply',
    },
    component: () => import('@views/mysql/apply/CreateModule.vue'),
  },
  {
    name: 'SelfServiceBindDbModule',
    path: 'bind-db-module/:type/:bk_biz_id/:db_module_id',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('绑定配置'),
      activeMenu: 'SelfServiceApply',
    },
    component: () => import('@views/mysql/apply/CreateModule.vue'),
  },
  {
    name: 'MysqlManage',
    path: 'mysql-manage',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('Mysql 集群管理'),
    },
    redirect: {
      name: 'DatabaseTendbha',
    },
    component: () => import('@views/mysql/Index.vue'),
    children: [
      {
        name: 'PermissionRules',
        path: 'permission-rules',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('MySQL_授权规则'),
          isMenu: true,
          submenuId: 'database-permission',
        },
        component: () => import('@views/mysql/permission/index.vue'),
      },
      {
        path: 'partition-manage',
        name: 'mysqlPartitionManage',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('Mysql 分区管理'),
          isMenu: true,
        },
        component: () => import('@views/mysql/partition-manage/Index.vue'),
      },
    ],
  },

];

export default function getRoutes(controller: Record<MySQLFunctions | 'mysql', boolean>) {
  // 关闭 mysql 功能
  if (controller.mysql !== true) {
    return [];
  }

  const renderRoutes = commonRouters.find(item => item.name === 'MysqlManage');

  if (!renderRoutes) {
    return commonRouters;
  }

  if (controller.tendbsingle) {
    renderRoutes.children?.push(...singleRoutes);
  }
  if (controller.tendbha) {
    renderRoutes.children?.push(...haRoutes);
  }
  if (controller.toolbox) {
    renderRoutes.children?.push(...mysqlToolboxRouters);
  }

  return commonRouters;
}
