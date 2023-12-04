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

import { t } from '@locales/index';

export const mysqlToolboxChildrenRouters: RouteRecordRaw[] = [
  {
    name: 'MySQLExecute',
    path: 'sql-execute/:step?',
    meta: {
      navName: t('变更SQL执行'),
    },
    component: () => import('@views/mysql/sql-execute/index.vue'),
  },
  {
    name: 'MySQLDBRename',
    path: 'db-rename',
    meta: {
      navName: t('DB重命名'),
    },
    component: () => import('@views/mysql/db-rename/index.vue'),
  },
  {
    name: 'MySQLPrivilegeCloneClient',
    path: 'privilege-clone-client',
    meta: {
      navName: t('客户端权限克隆'),
    },
    component: () => import('@views/mysql/privilege-clone-client/index.vue'),
  },
  {
    name: 'MySQLPrivilegeCloneInst',
    path: 'privilege-clone-inst',
    meta: {
      navName: t('DB实例权限克隆'),
    },
    component: () => import('@views/mysql/privilege-clone-inst/index.vue'),
  },
  {
    name: 'MySQLSlaveRebuild',
    path: 'slave-rebuild/:page?',
    meta: {
      navName: t('重建从库'),
    },
    component: () => import('@views/mysql/slave-rebuild/index.vue'),
  },
  {
    name: 'MySQLSlaveAdd',
    path: 'slave-add',
    meta: {
      navName: t('添加从库'),
    },
    component: () => import('@views/mysql/slave-add/index.vue'),
  },
  {
    name: 'MySQLMasterSlaveClone',
    path: 'master-slave-clone/:page?',
    meta: {
      navName: t('克隆主从'),
    },
    component: () => import('@views/mysql/master-slave-clone/index.vue'),
  },
  {
    name: 'MySQLMasterSlaveSwap',
    path: 'master-slave-swap/:page?',
    meta: {
      navName: t('主从互切'),
    },
    component: () => import('@views/mysql/master-slave-swap/index.vue'),
  },
  {
    name: 'MySQLProxyReplace',
    path: 'proxy-replace/:page?',
    meta: {
      navName: t('替换Proxy'),
    },
    component: () => import('@views/mysql/proxy-replace/index.vue'),
  },
  {
    name: 'MySQLProxyAdd',
    path: 'proxy-add/:page?',
    meta: {
      navName: t('添加Proxy'),
    },
    component: () => import('@views/mysql/proxy-add/index.vue'),
  },
  {
    name: 'MySQLMasterFailover',
    path: 'master-failover/:page?',
    meta: {
      navName: t('主库故障切换'),
    },
    component: () => import('@views/mysql/master-failover/index.vue'),
  },
  {
    name: 'MySQLDBTableBackup',
    path: 'db-table-backup/:page?',
    meta: {
      navName: t('库表备份'),
    },
    component: () => import('@views/mysql/db-table-backup/index.vue'),
  },
  {
    name: 'MySQLDBBackup',
    path: 'db-backup/:page?',
    meta: {
      navName: t('全库备份'),
    },
    component: () => import('@views/mysql/db-backup/index.vue'),
  },
  {
    name: 'MySQLDBClear',
    path: 'db-clear',
    meta: {
      navName: t('清档'),
    },
    component: () => import('@views/mysql/db-clear/index.vue'),
  },
  {
    name: 'MySQLDBRollback',
    path: 'rollback/:page?',
    meta: {
      navName: t('定点回档'),
    },
    component: () => import('@views/mysql/rollback/Index.vue'),
  },
  {
    name: 'MySQLDBFlashback',
    path: 'flashback/:page?',
    meta: {
      navName: t('闪回'),
    },
    component: () => import('@views/mysql/flashback/Index.vue'),
  },
  {
    name: 'MySQLChecksum',
    path: 'checksum',
    meta: {
      navName: t('数据校验修复'),
    },
    component: () => import('@views/mysql/checksum/Index.vue'),
  },
];

const singleRoutes: RouteRecordRaw[] = [
  {
    name: 'DatabaseTendbsingle',
    path: 'single-cluster-list',
    meta: {
      navName: t('MySQL单节点_集群管理'),
      fullscreen: true,
      skeleton: 'clusterList',
    },
    component: () => import('@views/mysql/single-cluster-list/Index.vue'),
  },
];

const haRoutes: RouteRecordRaw[] = [
  {
    name: 'DatabaseTendbha',
    path: 'ha-cluster-list',
    meta: {
      navName: t('MySQL主从集群_集群管理'),
      fullscreen: true,
      skeleton: 'clusterList',
    },
    component: () => import('@views/mysql/ha-cluster-list/Index.vue'),
  },
  {
    name: 'DatabaseTendbhaInstance',
    path: 'ha-instance-list',
    meta: {
      navName: t('MySQL主从集群_实例视图'),
      fullscreen: true,
      skeleton: 'clusterList',
    },
    component: () => import('@views/mysql/ha-instance-list/Index.vue'),
  },
];

const mysqlToolboxRouters: RouteRecordRaw[] = [
  {
    name: 'MySQLToolbox',
    path: 'toolbox',
    redirect: {
      name: 'MySQLExecute',
    },
    meta: {
      navName: t('工具箱'),
      fullscreen: true,

    },
    component: () => import('@views/mysql/toolbox/index.vue'),
    children: mysqlToolboxChildrenRouters,
  },
];

const commonRouters: RouteRecordRaw[] = [

  {
    name: 'MysqlManage',
    path: 'mysql-manage',
    meta: {
      navName: t('Mysql 集群管理'),
    },
    redirect: {
      name: 'DatabaseTendbha',
    },
    component: () => import('@views/mysql/Index.vue'),
    children: [
      {
        name: 'SelfServiceApplySingle',
        path: 'apply-single',
        meta: {
          navName: t('申请MySQL单节点部署'),
        },
        props: {
          type: TicketTypes.MYSQL_SINGLE_APPLY,
        },
        component: () => import('@views/mysql/apply/ApplyMySQL.vue'),
      },
      {
        name: 'SelfServiceApplyHa',
        path: 'apply-ha',
        meta: {
          navName: t('申请MySQL主从部署'),
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
          navName: t('新建模块'),
        },
        component: () => import('@views/mysql/apply/CreateModule.vue'),
      },
      {
        name: 'SelfServiceBindDbModule',
        path: 'bind-db-module/:type/:bk_biz_id/:db_module_id',
        meta: {
          navName: t('绑定配置'),
        },
        component: () => import('@views/mysql/apply/CreateModule.vue'),
      },
      {
        name: 'PermissionRules',
        path: 'permission-rules',
        meta: {
          navName: t('MySQL_授权规则'),
        },
        component: () => import('@views/mysql/permission/index.vue'),
      },
      {
        path: 'partition-manage',
        name: 'mysqlPartitionManage',
        meta: {
          navName: t('Mysql 分区管理'),
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
