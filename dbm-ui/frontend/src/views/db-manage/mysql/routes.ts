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
import FunctionControllModel from '@services/model/function-controller/functionController';

import { AccountTypes, DBTypes, TicketTypes } from '@common/const';

import { checkDbConsole, createToolboxRoute } from '@utils';

import { t } from '@locales/index';

const { createRouteItem } = createToolboxRoute(DBTypes.MYSQL);

export const mysqlToolboxChildrenRouters: RouteRecordRaw[] = [
  {
    path: 'sql-execute/:step?',
    name: 'MySQLExecute',
    meta: {
      navName: t('变更SQL执行'),
    },
    component: () => import('@views/db-manage/mysql/sql-execute/index.vue'),
  },
  createRouteItem(TicketTypes.MYSQL_RENAME_DATABASE, t('DB重命名')),
  {
    path: 'privilege-clone-client/:page?',
    name: 'MySQLPrivilegeCloneClient',
    meta: {
      navName: t('客户端权限克隆'),
    },
    component: () => import('@views/db-manage/mysql/privilege-clone-client/Index.vue'),
  },
  {
    path: 'privilege-clone-inst/:page?',
    name: 'MySQLPrivilegeCloneInst',
    meta: {
      navName: t('DB实例权限克隆'),
    },
    component: () => import('@views/db-manage/mysql/privilege-clone-inst/Index.vue'),
  },
  createRouteItem(TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE, t('重建从库')),
  createRouteItem(TicketTypes.MYSQL_RESTORE_SLAVE, t('重建从库')),
  createRouteItem(TicketTypes.MYSQL_ADD_SLAVE, t('添加从库')),
  createRouteItem(TicketTypes.MYSQL_MIGRATE_CLUSTER, t('迁移主从')),
  createRouteItem(TicketTypes.MYSQL_PROXY_ADD, t('添加Proxy')),
  createRouteItem(TicketTypes.MYSQL_MASTER_SLAVE_SWITCH, t('主从互切')),
  createRouteItem(TicketTypes.MYSQL_PROXY_SWITCH, t('替换Proxy')),
  createRouteItem(TicketTypes.MYSQL_MASTER_FAIL_OVER, t('主库故障切换')),
  createRouteItem(TicketTypes.MYSQL_INSTANCE_FAIL_OVER, t('主库故障切换')),
  {
    path: 'db-table-backup/:page?',
    name: 'MySQLDBTableBackup',
    meta: {
      navName: t('库表备份'),
    },
    component: () => import('@views/db-manage/mysql/db-table-backup/index.vue'),
  },
  {
    path: 'db-backup/:page?',
    name: 'MySQLDBBackup',
    meta: {
      navName: t('全库备份'),
    },
    component: () => import('@views/db-manage/mysql/db-backup/index.vue'),
  },
  {
    path: 'db-clear/:page?',
    name: 'MySQLDBClear',
    meta: {
      navName: t('清档'),
    },
    component: () => import('@views/db-manage/mysql/db-clear/Index.vue'),
  },
  createRouteItem(TicketTypes.MYSQL_ROLLBACK_CLUSTER, t('定点构造')),
  // 库表闪回
  {
    path: 'flashback/:page?',
    name: 'MySQLDBFlashback',
    meta: {
      navName: t('闪回'),
    },
    component: () => import('@views/db-manage/mysql/flashback/Index.vue'),
  },
  // 记录级闪回
  // 两个闪回两个路由，这里没问题
  createRouteItem(TicketTypes.MYSQL_FLASHBACK, t('闪回')),
  {
    path: 'checksum/:page?',
    name: 'MySQLChecksum',
    meta: {
      navName: t('数据校验修复'),
    },
    component: () => import('@views/db-manage/mysql/checksum/Index.vue'),
  },
  {
    path: 'openarea-template',
    name: 'MySQLOpenareaTemplate',
    meta: {
      navName: t('开区模版'),
    },
    component: () => import('@views/db-manage/mysql/openarea/template/Index.vue'),
  },
  {
    path: 'data-migrate/:page?',
    name: 'MySQLDataMigrate',
    meta: {
      navName: t('DB克隆'),
    },
    component: () => import('@views/db-manage/mysql/data-migrate/Index.vue'),
  },
  {
    path: 'webconsole',
    name: 'MySQLWebconsole',
    meta: {
      navName: 'Webconsole',
    },
    component: () => import('@views/db-manage/mysql/webconsole/Index.vue'),
  },
  createRouteItem(TicketTypes.MYSQL_PROXY_UPGRADE, t('版本升级')),
  createRouteItem(TicketTypes.MYSQL_CLUSTER_STANDARDIZE, t('集群标准化')),
];

const singleRoutes: RouteRecordRaw[] = [
  {
    path: 'tendbsingle',
    name: 'tendbsingle',
    meta: {
      fullscreen: true,
      navName: t('MySQL单节点_集群管理'),
      skeleton: 'clusterList',
    },
    redirect: {
      name: 'DatabaseTendbsingle',
    },
    component: () => import('@views/db-manage/mysql/Index.vue'),
    children: [
      {
        path: 'list/:clusterId?',
        name: 'DatabaseTendbsingle',
        meta: {
          fullscreen: true,
          navName: t('MySQL单节点_集群管理'),
          skeleton: 'clusterList',
        },
        component: () => import('@/views/db-manage/mysql/single-cluster-list/Index.vue'),
      },
      {
        path: 'detail/:clusterId',
        name: 'tendbsingleDetail',
        meta: {
          fullscreen: true,
          navName: t('MySQL单节点_集群详情'),
        },
        component: () => import('@views/db-manage/mysql/single-cluster-detail/Index.vue'),
      },
    ],
  },
];

const haRoutes: RouteRecordRaw[] = [
  {
    path: 'tendbha',
    name: 'tendbha',
    meta: {
      fullscreen: true,
      navName: t('MySQL主从集群_集群管理'),
      skeleton: 'clusterList',
    },
    redirect: {
      name: 'DatabaseTendbha',
    },
    component: () => import('@views/db-manage/mysql/Index.vue'),
    children: [
      {
        path: 'list/:clusterId?',
        name: 'DatabaseTendbha',
        meta: {
          fullscreen: true,
          navName: t('MySQL主从集群_集群管理'),
          skeleton: 'clusterList',
        },
        component: () => import('@views/db-manage/mysql/ha-cluster-list/Index.vue'),
      },
      {
        path: 'detail/:clusterId',
        name: 'tendbHaDetail',
        meta: {
          fullscreen: true,
          navName: t('MySQL主从集群_集群详情'),
        },
        component: () => import('@views/db-manage/mysql/ha-cluster-detail/Index.vue'),
      },
      {
        path: 'instance-list',
        name: 'DatabaseTendbhaInstance',
        meta: {
          fullscreen: true,
          navName: t('MySQL主从集群_实例视图'),
        },
        component: () => import('@views/db-manage/mysql/ha-instance-list/Index.vue'),
      },
    ],
  },
];

const mysqlToolboxRouters: RouteRecordRaw[] = [
  {
    path: 'toolbox',
    name: 'MySQLToolbox',
    meta: {
      fullscreen: true,
      navName: t('工具箱'),
    },
    redirect: {
      name: 'MySQLExecute',
    },
    component: () => import('@views/db-manage/mysql/toolbox/index.vue'),
    children: [
      ...mysqlToolboxChildrenRouters,
      {
        path: 'toolbox-result/:ticketType?/:ticketId?',
        name: 'MysqlToolboxResult',
        component: () => import('@views/db-manage/common/toolbox-result/Index.vue'),
      },
    ],
  },
];

const dumperDataSubscription = {
  path: 'dumper-data-subscribe/:dumperId(\\d+)?',
  name: 'DumperDataSubscription',
  meta: {
    fullscreen: true,
    navName: t('数据订阅'),
  },
  component: () => import('@views/db-manage/mysql/dumper/Index.vue'),
};

const commonRouters: RouteRecordRaw[] = [
  {
    path: 'mysql',
    name: 'MysqlManage',
    meta: {
      navName: t('Mysql 集群管理'),
    },
    redirect: {
      name: 'DatabaseTendbha',
    },
    component: () => import('@views/db-manage/mysql/Index.vue'),
    children: [
      {
        path: 'permission-rules',
        name: 'PermissionRules',
        meta: {
          navName: t('【MySQL】授权规则'),
        },
        component: () => import('@views/db-manage/mysql/permission/Index.vue'),
      },
      {
        path: 'permission-retrieve',
        name: 'MysqlPermissionRetrieve',
        meta: {
          navName: t('权限查询'),
        },
        props: { accountType: AccountTypes.MYSQL },
        component: () => import('@views/permission-retrieve/Index.vue'),
      },
      {
        path: 'whitelist',
        name: 'mysqlWhitelist',
        meta: {
          navName: t('授权白名单'),
        },
        component: () => import('@views/whitelist/list/Index.vue'),
      },
      {
        path: 'partition-manage',
        name: 'mysqlPartitionManage',
        meta: {
          navName: t('Mysql 分区管理'),
        },
        component: () => import('@views/db-manage/mysql/partition-manage/Index.vue'),
      },
      {
        path: 'openarea-template-create',
        name: 'MySQLOpenareaTemplateCreate',
        meta: {
          navName: t('新建开区模板'),
        },
        component: () => import('@views/db-manage/mysql/openarea/template-create/Index.vue'),
      },
      {
        path: 'openarea-template-edit/:id',
        name: 'MySQLOpenareaTemplateEdit',
        meta: {
          navName: t('编辑开区模板'),
        },
        component: () => import('@views/db-manage/mysql/openarea/template-create/Index.vue'),
      },
      {
        path: 'openarea-create/:id',
        name: 'mysqlOpenareaCreate',
        meta: {
          navName: t('新建开区'),
        },
        component: () => import('@views/db-manage/mysql/openarea/create/Index.vue'),
      },
    ],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<MySQLFunctions, 'mysql'>('mysql');
  // 关闭 mysql 功能
  if (controller.mysql !== true) {
    return [];
  }

  const renderRoutes = commonRouters.find((item) => item.name === 'MysqlManage');

  if (!renderRoutes) {
    return commonRouters;
  }

  if (checkDbConsole('mysql.dataSubscription')) {
    commonRouters[0].children!.push(dumperDataSubscription);
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
